import asyncio
import os
import shutil
import glob
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/config/.gemini/antigravity/brain/f6b49830-c82f-4b94-bd28-1f1078032999"
TEMP_VIDEO_DIR = "/tmp/playwright_videos"

async def record_demo():
    os.makedirs(TEMP_VIDEO_DIR, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=TEMP_VIDEO_DIR,
            record_video_size={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        print("Navigating to Memory Bank Agent frontend...")
        await page.goto("https://memory-bank-frontend-449481897749.us-east1.run.app")
        await page.wait_for_selector("header")
        await asyncio.sleep(2)

        # 1. Click prompt chip 1: "What allergies did I mention earlier?"
        print("Executing Prompt 1: What allergies did I mention earlier?")
        prompt1_chip = page.locator(".prompt-chip").first
        await prompt1_chip.click()
        
        # Wait for agent reply bubble / A2UI card
        await page.wait_for_selector(".msg.agent", timeout=45000)
        await asyncio.sleep(5)  # Showcase A2UI card response

        # 2. Type Prompt 2: "Store a new health record: Dairy sensitivity (Moderate)"
        print("Executing Prompt 2: Store a new health record: Dairy sensitivity (Moderate)")
        input_el = page.locator("#input")
        await input_el.fill("Store a new health record: Dairy sensitivity (Moderate)")
        await asyncio.sleep(1)
        await page.locator("form button").click()

        # Wait for second agent reply
        await page.wait_for_selector(".msg.agent:nth-of-type(4)", timeout=45000)
        await asyncio.sleep(5)  # Showcase database lookup & record confirmation

        await context.close()
        await browser.close()

    # Move generated MP4 video to artifact directory
    videos = glob.glob(os.path.join(TEMP_VIDEO_DIR, "*.webm")) + glob.glob(os.path.join(TEMP_VIDEO_DIR, "*.mp4"))
    if videos:
        latest_video = videos[0]
        dest_path = os.path.join(ARTIFACT_DIR, "demo_video.webm")
        shutil.copy(latest_video, dest_path)
        print(f"Demo video saved successfully to: {dest_path}")
        return dest_path
    else:
        print("No video recorded!")
        return None

if __name__ == "__main__":
    asyncio.run(record_demo())
