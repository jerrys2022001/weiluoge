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
  const mediaFiles = Array.isArray(config.mediaFiles) ? config.mediaFiles : [];
  for (const mediaFile of mediaFiles) {
    if (!fs.existsSync(mediaFile)) {
      throw new Error(`Media file not found: ${mediaFile}`);
    }
  }
  return config;
}

function ensureDirectory(targetPath) {
  fs.mkdirSync(targetPath, { recursive: true });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
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

function normalizeSnippet(value) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
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

async function waitForLoginIfNeeded(page, waitSeconds) {
  if (!waitSeconds || waitSeconds <= 0) {
    return false;
  }
  const deadline = Date.now() + waitSeconds * 1000;
  while (Date.now() < deadline) {
    if (!(await pageShowsLogin(page))) {
      return true;
    }
    await page.waitForTimeout(1500);
  }
  return !(await pageShowsLogin(page));
}

async function findTweetIdInCurrentView(page, excerpt) {
  const normalizedExcerpt = normalizeSnippet(excerpt);
  if (!normalizedExcerpt) {
    return null;
  }

  const articles = page.locator("article");
  const count = await articles.count().catch(() => 0);
  for (let index = 0; index < Math.min(count, 8); index += 1) {
    const article = articles.nth(index);
    const text = await article.textContent().catch(() => "");
    if (!normalizeSnippet(text).includes(normalizedExcerpt)) {
      continue;
    }
    const href = await article
      .locator('a[href*="/status/"]')
      .first()
      .getAttribute("href")
      .catch(() => null);
    if (!href) {
      continue;
    }
    const match = href.match(/status\/(\d+)/);
    if (match) {
      return match[1];
    }
  }
  return null;
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
  return findTweetIdInCurrentView(page, excerpt);
}

async function confirmTweetIdAfterPosting(page, screenName, excerpt) {
  const attempts = [
    async () => findTweetIdInCurrentView(page, excerpt),
    async () => {
      if (!screenName) {
        return null;
      }
      return findTweetIdOnProfile(page, screenName, excerpt);
    },
    async () => {
      await page.goto("https://x.com/home", {
        waitUntil: "domcontentloaded",
        timeout: 60000,
      });
      await page.waitForTimeout(2500);
      return findTweetIdInCurrentView(page, excerpt);
    },
  ];

  for (let round = 0; round < 3; round += 1) {
    for (const attempt of attempts) {
      const tweetId = await attempt().catch(() => null);
      if (tweetId) {
        return tweetId;
      }
    }
    await page.waitForTimeout(3000);
  }
  return null;
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

async function attachMediaIfNeeded(page, mediaFiles) {
  if (!Array.isArray(mediaFiles) || mediaFiles.length === 0) {
    return;
  }

  const fileInput = page
    .locator('input[data-testid="fileInput"], input[type="file"][accept*="image"], input[type="file"]')
    .first();
  await fileInput.waitFor({ state: "attached", timeout: 30000 });
  await fileInput.setInputFiles(mediaFiles);

  const preview = page
    .locator(
      '[data-testid="attachments"], [data-testid="mediaPreview"], [data-testid="previewInterstitial"], img[src^="blob:"]'
    )
    .first();
  await preview.waitFor({ state: "visible", timeout: 60000 }).catch(async () => {
    await page.waitForTimeout(5000);
  });
}

async function waitForPostButtonEnabled(page, postButton, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (!(await postButton.isDisabled().catch(() => true))) {
      return;
    }
    await page.waitForTimeout(500);
  }
  throw new Error("X post button stayed disabled after preparing the composer.");
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
          proxyServer: config.proxyServer || null,
          mediaFiles: Array.isArray(config.mediaFiles) ? config.mediaFiles : [],
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
  const lockFile = path.join(config.outputDir, "x-playwright-driver.lock");
  let lockFd = null;

  try {
    try {
      if (fs.existsSync(lockFile)) {
        const stat = fs.statSync(lockFile);
        const ageMs = Date.now() - stat.mtimeMs;
        let removeStaleLock = ageMs > 90 * 1000;
        try {
          const existingPid = Number(fs.readFileSync(lockFile, "utf8").trim());
          if (existingPid) {
            try {
              process.kill(existingPid, 0);
            } catch {
              removeStaleLock = true;
            }
          }
        } catch {
          removeStaleLock = true;
        }
        if (removeStaleLock) {
          fs.unlinkSync(lockFile);
        }
      }
      lockFd = fs.openSync(lockFile, "wx");
      fs.writeFileSync(lockFd, `${process.pid}`);
    } catch {
      throw new Error("Another Playwright X posting session is already running.");
    }

    let lastLaunchError = null;
    for (let attempt = 0; attempt < 3; attempt += 1) {
      try {
        context = await chromium.launchPersistentContext(config.userDataDir, {
          headless: false,
          executablePath: config.chromePath,
          proxy: config.proxyServer ? { server: config.proxyServer } : undefined,
          args: [`--profile-directory=${config.profileDirectory || "Default"}`],
          viewport: { width: 1440, height: 960 },
        });
        lastLaunchError = null;
        break;
      } catch (error) {
        lastLaunchError = error;
        await sleep(2500 * (attempt + 1));
      }
    }
    if (!context) {
      throw lastLaunchError || new Error("Unable to launch persistent Chrome context.");
    }

    page = context.pages()[0] || (await context.newPage());
    const composeUrl = config.replyTo
      ? `https://x.com/compose/post?in_reply_to=${encodeURIComponent(config.replyTo)}`
      : "https://x.com/compose/post";
    await page.goto(composeUrl, {
      waitUntil: "domcontentloaded",
      timeout: 60000,
    });

    if (await pageShowsLogin(page)) {
      const loggedIn = await waitForLoginIfNeeded(page, Number(config.loginWaitSeconds || 0));
      if (!loggedIn) {
        throw new Error("X login is required in the selected Chrome profile.");
      }
    }

    const editor = page.locator('[data-testid="tweetTextarea_0"]').first();
    try {
      await editor.waitFor({ state: "visible", timeout: 60000 });
    } catch (error) {
      if (await pageShowsLogin(page)) {
        const loggedIn = await waitForLoginIfNeeded(page, Number(config.loginWaitSeconds || 0));
        if (!loggedIn) {
          throw new Error("X login is required in the selected Chrome profile.");
        }
        await editor.waitFor({ state: "visible", timeout: 60000 });
      } else {
        throw error;
      }
    }
    await editor.click();
    await page.keyboard.insertText(config.text);
    await attachMediaIfNeeded(page, config.mediaFiles);

    const postButton = page
      .locator('[data-testid="tweetButtonInline"], [data-testid="tweetButton"]')
      .first();
    await postButton.waitFor({ state: "visible", timeout: 30000 });
    await waitForPostButtonEnabled(page, postButton, 60000);

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
      tweetId = await confirmTweetIdAfterPosting(page, screenName, excerpt);
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
  } finally {
    try {
      if (lockFd !== null) {
        fs.closeSync(lockFd);
      }
      if (fs.existsSync(lockFile)) {
        fs.unlinkSync(lockFile);
      }
    } catch {
      // ignore cleanup failures
    }
  }
}

main().catch((error) => {
  const message = error && error.stack ? error.stack : String(error);
  process.stderr.write(`${message}\n`);
  process.exit(1);
});
