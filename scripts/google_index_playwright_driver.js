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

function ensureDirectory(targetPath) {
  fs.mkdirSync(targetPath, { recursive: true });
}

function readConfig(configPath) {
  const raw = fs.readFileSync(configPath, "utf8");
  const config = JSON.parse(raw);
  if (!config.mode) {
    throw new Error("Missing required config.mode.");
  }
  if (!config.siteUrl) {
    throw new Error("Missing required config.siteUrl.");
  }
  return config;
}

function propertyUrl(siteUrl) {
  return `https://search.google.com/search-console?resource_id=${encodeURIComponent(siteUrl)}`;
}

function inspectUrl(siteUrl, targetUrl) {
  return (
    `https://search.google.com/search-console/inspect` +
    `?resource_id=${encodeURIComponent(siteUrl)}` +
    `&id=${encodeURIComponent(targetUrl)}`
  );
}

function safeSlug(input) {
  return String(input || "")
    .replace(/^https?:\/\//i, "")
    .replace(/[^a-zA-Z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 80);
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

async function pageShowsGoogleLogin(page) {
  if (!page) {
    return false;
  }
  if (page.url().includes("accounts.google.com")) {
    return true;
  }
  const emailInputCount = await page.locator('input[type="email"]').count().catch(() => 0);
  if (emailInputCount > 0) {
    return true;
  }
  const passwordInputCount = await page.locator('input[type="password"]').count().catch(() => 0);
  return passwordInputCount > 0;
}

async function getBodyText(page) {
  return (await page.textContent("body").catch(() => "")) || "";
}

async function pageShowsSearchConsoleMarketing(page) {
  const bodyText = await getBodyText(page);
  return /Start now|Get started|立即使用|提升您的网站在 Google 搜索结果中的排名|Search Console 中的工具与报告可帮助您/i.test(
    bodyText
  );
}

async function findStartNowButton(page) {
  const candidates = [
    page.getByRole("link", { name: /Start now|Get started|立即使用/i }).first(),
    page.getByRole("button", { name: /Start now|Get started|立即使用/i }).first(),
    page.getByText(/Start now|Get started|立即使用/i).first(),
  ];

  for (const candidate of candidates) {
    const count = await candidate.count().catch(() => 0);
    if (count > 0) {
      return candidate;
    }
  }
  return null;
}

function urlLooksLikePropertyPage(url) {
  return /search\.google\.com\/search-console/i.test(url) && /[?&]resource_id=/i.test(url);
}

function urlLooksLikeInspectionPage(url) {
  return /search\.google\.com\/search-console\/inspect/i.test(url);
}

async function waitForSearchConsoleAccess(page, siteUrl, timeoutMs) {
  await page.goto(propertyUrl(siteUrl), {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });

  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await pageShowsGoogleLogin(page)) {
      await page.waitForTimeout(1500);
      continue;
    }

    if (await pageShowsSearchConsoleMarketing(page)) {
      const startNowButton = await findStartNowButton(page);
      if (startNowButton) {
        await startNowButton.click().catch(() => {});
        await page.waitForTimeout(2000);
        continue;
      }
    }

    const currentUrl = page.url();
    if (urlLooksLikePropertyPage(currentUrl) && !(await pageShowsSearchConsoleMarketing(page))) {
      return;
    }

    const hasInspectionEntry =
      (await page.getByText(/URL inspection|网址检查/i).first().count().catch(() => 0)) > 0;
    if (hasInspectionEntry && !(await pageShowsSearchConsoleMarketing(page))) {
      return;
    }
    await page.waitForTimeout(1500);
  }

  if (await pageShowsGoogleLogin(page)) {
    throw new Error("Google login is required in the selected browser profile.");
  }
  throw new Error("Search Console did not become ready before timeout.");
}

async function findRequestIndexingButton(page) {
  const candidates = [
    page.getByRole("button", { name: /Request indexing/i }).first(),
    page.getByRole("button", { name: /请求编入索引/ }).first(),
    page.getByText(/Request indexing/i).locator("..").first(),
    page.getByText(/请求编入索引/).locator("..").first(),
  ];

  for (const candidate of candidates) {
    const count = await candidate.count().catch(() => 0);
    if (count > 0) {
      return candidate;
    }
  }
  return null;
}

async function findLiveTestButton(page) {
  const candidates = [
    page.getByRole("button", { name: /Test live URL/i }).first(),
    page.getByRole("button", { name: /测试实时网址/ }).first(),
  ];

  for (const candidate of candidates) {
    const count = await candidate.count().catch(() => 0);
    if (count > 0) {
      return candidate;
    }
  }
  return null;
}

async function waitForInspectionState(page, timeoutMs, options = {}) {
  const allowManualLogin = Boolean(options.allowManualLogin);
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await pageShowsGoogleLogin(page)) {
      if (allowManualLogin) {
        await page.waitForTimeout(1500);
        continue;
      }
      throw new Error("Google login is required in the selected browser profile.");
    }

    if (await pageShowsSearchConsoleMarketing(page)) {
      await page.waitForTimeout(1500);
      continue;
    }

    const requestButton = await findRequestIndexingButton(page);
    if (requestButton) {
      return { requestButton, liveTestButton: await findLiveTestButton(page) };
    }

    const liveTestButton = await findLiveTestButton(page);
    if (liveTestButton) {
      return { requestButton: null, liveTestButton };
    }

    const bodyText = await getBodyText(page);
    if (
      urlLooksLikeInspectionPage(page.url()) &&
      /URL is on Google|URL is not on Google|网址已在 Google 上|网址不在 Google 上|Coverage|Indexing/i.test(
        bodyText || ""
      )
    ) {
      return { requestButton: null, liveTestButton: await findLiveTestButton(page) };
    }
    await page.waitForTimeout(1500);
  }
  return { requestButton: null, liveTestButton: null };
}

async function waitForRequestConfirmation(page, timeoutMs) {
  const patterns = [
    /Indexing requested/i,
    /Request submitted/i,
    /已发送编入索引请求/,
    /已请求编入索引/,
    /编入索引请求已发送/,
  ];

  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const bodyText = await page.textContent("body").catch(() => "");
    if (patterns.some((pattern) => pattern.test(bodyText || ""))) {
      return true;
    }
    await page.waitForTimeout(1200);
  }
  return false;
}

async function inspectAndRequest(page, config, targetUrl) {
  const targetInspectUrl = inspectUrl(config.siteUrl, targetUrl);
  const artifactBase = safeSlug(targetUrl);
  const screenshotPath = path.join(config.outputDir, `${artifactBase || "url"}.png`);

  await page.goto(targetInspectUrl, {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });

  const { requestButton, liveTestButton } = await waitForInspectionState(
    page,
    (config.timeoutSeconds || 180) * 1000
  );

  let status = "already_submitted_or_unavailable";
  let note = "";

  if (requestButton) {
    const disabled = await requestButton.isDisabled().catch(() => false);
    if (disabled) {
      status = "request_button_disabled";
      note = "Request indexing button is visible but disabled.";
    } else {
      try {
        await requestButton.click({ timeout: 15000 });
      } catch {
        await requestButton.click({ force: true, timeout: 5000 });
      }
      const confirmed = await waitForRequestConfirmation(page, 45000);
      status = confirmed ? "requested" : "clicked_request_button";
      note = confirmed
        ? "Search Console confirmed the indexing request."
        : "Clicked the request button but did not see a localized confirmation string.";
    }
  } else if (liveTestButton) {
    status = "already_submitted_or_unavailable";
    note = "Inspection page loaded without a request button. URL may already be pending or unavailable for manual request.";
  } else {
    status = "request_button_missing";
    note = "Inspection page loaded but the request indexing button was not found.";
  }

  await screenshotIfPossible(page, screenshotPath);

  return {
    url: targetUrl,
    inspectUrl: targetInspectUrl,
    status,
    note,
    screenshotPath,
  };
}

async function runAuthMode(page, config) {
  await waitForSearchConsoleAccess(page, config.siteUrl, (config.timeoutSeconds || 600) * 1000);
  await page.goto(inspectUrl(config.siteUrl, config.siteUrl), {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });
  await waitForInspectionState(page, (config.timeoutSeconds || 600) * 1000, {
    allowManualLogin: true,
  });
  const screenshotPath = path.join(config.outputDir, "auth-ready.png");
  await screenshotIfPossible(page, screenshotPath);
  return {
    ok: true,
    mode: "auth",
    siteUrl: config.siteUrl,
    screenshotPath,
    message: "Search Console login looks ready in the selected browser profile.",
  };
}

async function runRequestMode(page, config) {
  await waitForSearchConsoleAccess(page, config.siteUrl, 120000);

  const results = [];
  for (const targetUrl of config.urls || []) {
    const result = await inspectAndRequest(page, config, targetUrl);
    results.push(result);
  }

  return {
    ok: true,
    mode: "requestIndexing",
    siteUrl: config.siteUrl,
    results,
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const config = readConfig(args.config);
  ensureDirectory(config.outputDir);
  ensureDirectory(config.userDataDir);

  let context;
  let page;

  try {
    context = await chromium.launchPersistentContext(config.userDataDir, {
      headless: false,
      executablePath: config.chromePath,
      args: [`--profile-directory=${config.profileDirectory || "Default"}`],
      viewport: { width: 1440, height: 960 },
    });

    page = context.pages()[0] || (await context.newPage());

    let payload;
    if (config.mode === "auth") {
      payload = await runAuthMode(page, config);
    } else if (config.mode === "requestIndexing") {
      payload = await runRequestMode(page, config);
    } else {
      throw new Error(`Unsupported mode: ${config.mode}`);
    }

    await context.close();
    process.stdout.write(JSON.stringify(payload, null, 2));
  } catch (error) {
    const failureShot = path.join(config.outputDir, "google-index-failure.png");
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
