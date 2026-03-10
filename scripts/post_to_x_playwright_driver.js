#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

function parseArgs(argv) {
  const output = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === "--config") {
      output.config = argv[index + 1];
      index += 1;
      continue;
    }
    throw new Error(`Unsupported argument: ${token}`);
  }
  if (!output.config) {
    throw new Error("Missing required --config argument.");
  }
  return output;
}

function readConfig(configPath) {
  const raw = fs.readFileSync(configPath, "utf8");
  const config = JSON.parse(raw);
  if (!config.text || !String(config.text).trim()) {
    throw new Error("Tweet text is empty.");
  }
  return config;
}

function ensureDirectory(targetPath) {
  fs.mkdirSync(targetPath, { recursive: true });
}

function extractScreenName(accountText) {
  const match = String(accountText || "").match(/@([A-Za-z0-9_]{1,15})/);
  return match ? match[1] : null;
}

function extractTweetId(payload) {
  const candidates = [
    payload?.data?.create_tweet?.tweet_results?.result?.rest_id,
    payload?.data?.create_tweet?.tweet_result?.result?.rest_id,
    payload?.data?.create_note_tweet?.tweet_results?.result?.rest_id,
    payload?.data?.create_post?.tweet_results?.result?.rest_id,
  ];
  for (const candidate of candidates) {
    if (candidate) {
      return String(candidate);
    }
  }
  return null;
}

async function screenshotIfPossible(page, filePath) {
  if (!page || !filePath) {
    return;
  }
  try {
    await page.screenshot({ path: filePath, fullPage: true });
  } catch {
    // Ignore screenshot failures during cleanup.
  }
}

async function pageShowsLogin(page) {
  if (!page) {
    return false;
  }
  if (page.url().includes("/i/flow/login")) {
    return true;
  }
  const loginInputCount = await page.locator('input[name="text"]').count().catch(() => 0);
  return loginInputCount > 0;
}

async function findTweetIdOnProfile(page, screenName, excerpt) {
  if (!screenName || !excerpt) {
    return null;
  }
  await page.goto(`https://x.com/${screenName}`, {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });
  await page.waitForTimeout(3000);
  const article = page.locator("article").filter({ hasText: excerpt }).first();
  if ((await article.count()) === 0) {
    return null;
  }
  const href = await article
    .locator('a[href*="/status/"]')
    .first()
    .getAttribute("href")
    .catch(() => null);
  if (!href) {
    return null;
  }
  const match = href.match(/status\/(\d+)/);
  return match ? match[1] : null;
}

async function submitTweet(page, postButton) {
  try {
    await postButton.click({ timeout: 10000 });
    return;
  } catch {
    // Fall through to stronger submit paths.
  }

  try {
    await postButton.click({ force: true, timeout: 5000 });
    return;
  } catch {
    // Fall through to DOM click.
  }

  try {
    await postButton.evaluate((node) => node.click());
    return;
  } catch {
    // Fall through to keyboard shortcut.
  }

  await page.keyboard.press(process.platform === "darwin" ? "Meta+Enter" : "Control+Enter");
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const config = readConfig(args.config);
  ensureDirectory(config.outputDir);

  if (config.dryRun) {
    process.stdout.write(
      JSON.stringify(
        {
          ok: true,
          dryRun: true,
          method: "playwright",
          chromePath: config.chromePath,
          userDataDir: config.userDataDir,
          profileDirectory: config.profileDirectory || "Default",
          outputDir: config.outputDir,
        },
        null,
        2
      )
    );
    return;
  }

  let context;
  let page;
  const successShot = path.join(config.outputDir, "x-post-success.png");
  const failureShot = path.join(config.outputDir, "x-post-failure.png");

  try {
    context = await chromium.launchPersistentContext(config.userDataDir, {
      headless: false,
      executablePath: config.chromePath,
      args: [`--profile-directory=${config.profileDirectory || "Default"}`],
      viewport: { width: 1440, height: 960 },
    });

    page = context.pages()[0] || (await context.newPage());
    const composeUrl = config.replyTo
      ? `https://x.com/compose/post?in_reply_to=${encodeURIComponent(config.replyTo)}`
      : "https://x.com/compose/post";
    await page.goto(composeUrl, {
      waitUntil: "domcontentloaded",
      timeout: 60000,
    });

    if (await pageShowsLogin(page)) {
      throw new Error("X login is required in the selected Chrome profile.");
    }

    const editor = page.locator('[data-testid="tweetTextarea_0"]').first();
    try {
      await editor.waitFor({ state: "visible", timeout: 60000 });
    } catch (error) {
      if (await pageShowsLogin(page)) {
        throw new Error("X login is required in the selected Chrome profile.");
      }
      throw error;
    }
    await editor.click();
    await page.keyboard.insertText(config.text);

    const postButton = page
      .locator('[data-testid="tweetButtonInline"], [data-testid="tweetButton"]')
      .first();
    await postButton.waitFor({ state: "visible", timeout: 30000 });
    await page.waitForTimeout(500);
    if (await postButton.isDisabled()) {
      throw new Error("X post button is disabled after filling the composer.");
    }

    const responsePromise = page
      .waitForResponse(
        (response) =>
          response.request().method() === "POST" &&
          /CreateTweet|CreateNoteTweet|CreatePost/i.test(response.url()),
        { timeout: 60000 }
      )
      .catch(() => null);

    const accountText = await page
      .locator('[data-testid="SideNav_AccountSwitcher_Button"]')
      .first()
      .textContent()
      .catch(() => "");
    const screenName = extractScreenName(accountText);
    const excerpt = String(config.text).slice(0, 40);

    await submitTweet(page, postButton);

    const response = await responsePromise;
    const payload = response ? await response.json().catch(() => null) : null;
    let tweetId = extractTweetId(payload);
    if (!tweetId) {
      tweetId = await findTweetIdOnProfile(page, screenName, excerpt);
    }
    if (!tweetId) {
      throw new Error("Playwright posted but could not confirm the resulting tweet id.");
    }

    const tweetUrl = screenName ? `https://x.com/${screenName}/status/${tweetId}` : null;
    if (tweetUrl) {
      await page.goto(tweetUrl, {
        waitUntil: "domcontentloaded",
        timeout: 60000,
      });
    }
    await screenshotIfPossible(page, successShot);
    await context.close();

    process.stdout.write(
      JSON.stringify(
        {
          ok: true,
          method: "playwright",
          tweetId,
          tweetUrl,
          screenshotPath: successShot,
        },
        null,
        2
      )
    );
  } catch (error) {
    await screenshotIfPossible(page, failureShot);
    if (context) {
      await context.close().catch(() => {});
    }
    const message = error && error.stack ? error.stack : String(error);
    const suffix = fs.existsSync(failureShot) ? `\nScreenshot: ${failureShot}` : "";
    process.stderr.write(`${message}${suffix}\n`);
    process.exit(1);
  }
}

main().catch((error) => {
  const message = error && error.stack ? error.stack : String(error);
  process.stderr.write(`${message}\n`);
  process.exit(1);
});
