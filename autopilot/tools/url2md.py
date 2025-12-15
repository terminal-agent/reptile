import asyncio

import typer
from bs4 import BeautifulSoup
from markdownify import markdownify
from playwright.async_api import Page, async_playwright
from typing_extensions import Annotated

from .tool import TOOLS, CLITool


async def wait_till_html_rendered(page: Page, timeout: int = 30000):
  # Wait for the page to load completely
  # https://stackoverflow.com/questions/52497252/puppeteer-wait-until-page-is-completely-loaded
  # There is not stable way to check if the page is fully rendered
  # so we will check the size of the HTML content is static for a certain
  # period of time.
  check_duration_msecs = 1000
  max_checks = timeout // check_duration_msecs
  last_html_size = 0
  check_counts = 1
  count_stable_size_iterations = 0
  min_stable_size_iterations = 3

  while check_counts <= max_checks:
    html = await page.content()
    current_html_size = len(html)
    if last_html_size != 0 and current_html_size == last_html_size:
      count_stable_size_iterations += 1
    else:
      count_stable_size_iterations = 0  # reset the counter
    if count_stable_size_iterations >= min_stable_size_iterations:
      break
    last_html_size = current_html_size
    await page.wait_for_timeout(check_duration_msecs)
    check_counts += 1


@TOOLS.register
class Url2Md(CLITool):
  name = "url2md"
  description = """
  Convert a URL to Markdown.
  Usage:
  ```sh
  url2md <url>
  ```
  """

  def register(self):
    self.app.command()(self.url2md)

  def url2md(
    self,
    url: Annotated[str, typer.Argument(help="The URL to convert to Markdown.")],
  ):
    if not url.startswith("http://") and not url.startswith("https://"):
      url = "https://" + url
    print(f"Fetching content from: {url}")

    async def main():
      async with async_playwright() as p:
        browser = await p.chromium.launch(
          headless=False, args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
          user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto(url)
        await wait_till_html_rendered(page)
        # get content from page
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        for script in soup.find_all("script"):
          script.decompose()
        for style in soup.find_all("style"):
          style.decompose()
        for img in soup.find_all("img"):
          img.decompose()
        markdown = markdownify(str(soup), strip=["a"])
        # TODO: sometimes the link of a could be important, so we should
        # simplify them into indexes and keep the real link in another file
        # sequentially according to the index.
        await browser.close()
        return markdown

    markdown = asyncio.run(main())
    print(markdown)
