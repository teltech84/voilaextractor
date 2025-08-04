import requests
import json
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import re
import os
import glob
import sys
import subprocess


class VoilaFocusedScraper:
    def __init__(self, headless=True):
        self.seen_product_names = set()
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except ImportError:
            print("webdriver-manager not found, using default ChromeDriver")
            self.driver = webdriver.Chrome(options=chrome_options)

        self.driver.set_page_load_timeout(30)
        self.driver.implicitly_wait(5)

        self.products = []
        self.max_retries = 2

        self.target_categories = {
            "Fresh Fruits & Vegetables": "https://voila.ca/categories/fresh-fruits-vegetables/WEB1100606",
            "Meat & Seafood": "https://voila.ca/categories/meat-seafood/WEB1100609",
            "Dairy & Eggs": "https://voila.ca/categories/dairy-eggs/WEB1100610",
            "Cheese": "https://voila.ca/categories/cheese/WEB1504630?source=navigation",
            #"Bread & Bakery": "https://voila.ca/categories/bread-bakery/WEB1100608",
            "Deli": "https://voila.ca/categories/deli/WEB1100607",
            "Frozen Foods": "https://voila.ca/categories/frozen-foods/WEB1100612",
            #"Pantry": "https://voila.ca/categories/pantry/WEB1100615",
            "Scene+ Deals": "https://voila.ca/categories/scene-deals/WEB18638414?source=navigation",
            "Flyer Deals": "https://voila.ca/categories/flyer-deals/WEB19082285?source=navigation"
        }

    def check_existing_files(self):
        category_files = {}
        for category_name in self.target_categories.keys():
            safe_filename = re.sub(r'[^\w\-_\.]', '_', category_name.lower())
            filename = f"voila_{safe_filename}.csv"
            category_files[category_name] = filename

        existing_files = []
        missing_categories = []

        for category_name, filename in category_files.items():
            if os.path.exists(filename):
                existing_files.append((category_name, filename))
            else:
                missing_categories.append(category_name)

        other_files = [
            "voila_focused_groceries_progress.csv",
            "voila_budget_items_progress.csv",
            "voila_focused_groceries_FINAL.csv",
            "voila_budget_items_FINAL.csv"
        ]
        existing_other_files = [f for f in other_files if os.path.exists(f)]

        return existing_files, missing_categories, existing_other_files

    def load_existing_products(self):
        print("Loading existing products from CSV files...")

        if os.path.exists("voila_focused_groceries_progress.csv"):
            try:
                df = pd.read_csv("voila_focused_groceries_progress.csv")
                self.products = df.to_dict('records')
                print(f"✅ Loaded {len(self.products)} existing products from progress file")
                return
            except Exception as e:
                print(f"⚠️  Error loading progress file: {e}")

        existing_files, _, _ = self.check_existing_files()

        for category_name, filename in existing_files:
            try:
                df = pd.read_csv(filename)
                category_products = df.to_dict('records')
                self.products.extend(category_products)
                print(f"✅ Loaded {len(category_products)} products from {filename}")
            except Exception as e:
                print(f"⚠️  Error loading {filename}: {e}")

        if self.products:
            print(f"📊 Total loaded: {len(self.products)} products")

    def auto_continue_from_existing(self):
        existing_files, missing_categories, other_files = self.check_existing_files()

        if not existing_files and not other_files:
            print("🆕 No existing CSV files found. Starting fresh scraping...")
            return list(self.target_categories.keys())

        print("\n" + "=" * 60)
        print("📁 AUTO-RESTART: EXISTING FILES DETECTED")
        print("=" * 60)

        if existing_files:
            print("✅ Found completed categories:")
            for category_name, filename in existing_files:
                print(f"  - {category_name}: {filename}")

        if missing_categories:
            print(f"\n🔄 Auto-continuing with {len(missing_categories)} missing categories:")
            for category in missing_categories:
                print(f"  - {category}")

            self.load_existing_products()
            return missing_categories
        else:
            print("\n✅ All categories appear to be complete!")
            return []

    def is_auto_restart(self):
        return len(sys.argv) > 1 and sys.argv[1] == "--auto-restart"

    def handle_existing_files(self):
        existing_files, missing_categories, other_files = self.check_existing_files()

        if not existing_files and not other_files:
            print("🆕 No existing CSV files found. Starting fresh scraping...")
            return list(self.target_categories.keys())

        print("\n" + "=" * 60)
        print("📁 EXISTING FILES DETECTED")
        print("=" * 60)

        if existing_files:
            print("✅ Found category files:")
            for category_name, filename in existing_files:
                print(f"  - {category_name}: {filename}")

        if other_files:
            print("✅ Found other files:")
            for filename in other_files:
                print(f"  - {filename}")

        if missing_categories:
            print(f"\n❌ Missing categories ({len(missing_categories)}):")
            for category in missing_categories:
                print(f"  - {category}")
        else:
            print("\n✅ All categories appear to be complete!")

        print("\n" + "=" * 60)
        print("CHOOSE AN OPTION:")
        print("=" * 60)
        print("1. Continue from missing categories only")
        print("2. Delete all files and start completely fresh")
        print("3. Exit (do nothing)")

        while True:
            choice = input("\nEnter your choice (1, 2, or 3): ").strip()

            if choice == '1':
                if missing_categories:
                    print(f"\n🔄 Continuing with {len(missing_categories)} missing categories...")
                    self.load_existing_products()
                    return missing_categories
                else:
                    print("\n✅ All categories complete! Nothing to scrape.")
                    return []

            elif choice == '2':
                print("\n🗑️  Deleting all existing files...")

                for _, filename in existing_files:
                    try:
                        os.remove(filename)
                        print(f"  Deleted: {filename}")
                    except Exception as e:
                        print(f"  Error deleting {filename}: {e}")

                for filename in other_files:
                    try:
                        os.remove(filename)
                        print(f"  Deleted: {filename}")
                    except Exception as e:
                        print(f"  Error deleting {filename}: {e}")

                print("🆕 Starting completely fresh scraping...")
                return list(self.target_categories.keys())

            elif choice == '3':
                print("\n👋 Exiting without changes...")
                return None

            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3.")

    def fast_process_products(self, category_name, cards):
        new_products = 0

        for card in cards:
            try:
                text = card.text.strip()
                if len(text) < 10:
                    continue

                lines = [line.strip() for line in text.split('\n') if line.strip()]
                if len(lines) < 1:
                    continue

                name = None
                for line in lines:
                    skip_terms = ['add', 'cart', 'price']
                    if len(line) > 2 and not any(skip in line.lower() for skip in skip_terms):
                        name = line
                        break

                if not name or name in self.seen_product_names:
                    continue

                # Extract price directly from span with data-test='fop-price'
                price = 0.0
                try:
                    price_element = card.find_element(By.CSS_SELECTOR, "span[data-test='fop-price']")
                    price_text = price_element.text.strip()
                    if price_text.startswith('$'):
                        price = float(price_text[1:])
                except Exception:
                    price = 0.0

                size = 'Unknown'
                for line in lines:
                    size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:g|kg|lb|oz|ml|l|pack|ct|count|each|pc|lbs))', line,
                                           re.IGNORECASE)
                    if size_match:
                        size = size_match.group(1)
                        break

                promotion = None
                try:
                    promo_elem = card.find_element(By.CSS_SELECTOR, "span[data-test='fop-offer-text']")
                    promotion = promo_elem.text.strip()
                except Exception:
                    promotion = None

                product = {
                    'name': name,
                    'price': price,
                    'size': size,
                    'unit_price': None,
                    'category': category_name,
                    'has_price': price > 0,
                    'promotion': promotion
                }

                self.products.append(product)
                self.seen_product_names.add(name)
                new_products += 1

            except Exception:
                continue

        return new_products

    def scrape_category(self, category_name, category_url):
        print(f"\n{'=' * 50}")
        print(f"FAST SCRAPING: {category_name}")
        print(f"URL: {category_url}")
        print(f"{'=' * 50}")

        try:
            self.driver.get(category_url)
            time.sleep(2)

            initial_count = len(self.products)

            print(f"Starting infinite scroll for ALL products...")

            products_collected = 0
            scroll_count = 0
            no_growth_count = 0

            while scroll_count < 100 and products_collected < 1000:
                current_height = self.driver.execute_script("return document.body.scrollHeight")

                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)  # Wait longer for lazy loading

                new_height = self.driver.execute_script("return document.body.scrollHeight")
                page_grew = new_height > current_height
                scroll_count += 1

                if page_grew:
                    try:
                        # Re-fetch fresh product cards every scroll
                        cards = self.driver.find_elements(By.CSS_SELECTOR, "[class*='product-card']")
                        new_products = self.fast_process_products(category_name, cards)
                        products_collected = len([p for p in self.products if p.get('category') == category_name])
                        print(
                            f"  Scroll {scroll_count}: Found {new_products} new products. Total: {products_collected}")
                        no_growth_count = 0
                    except Exception as e:
                        print(f"  Scroll {scroll_count}: Error processing products: {e}")
                else:
                    no_growth_count += 1
                    print(f"  Scroll {scroll_count}: No page growth ({no_growth_count}/5)")
                    if no_growth_count >= 5:
                        print("  End of product list reached.")
                        break

            # Final fetch & process to catch anything missed at bottom
            try:
                final_cards = self.driver.find_elements(By.CSS_SELECTOR, "[class*='product-card']")
                final_new = self.fast_process_products(category_name, final_cards)
                final_total = len([p for p in self.products if p.get('category') == category_name])
                print(f"✅ INFINITE SCROLL COMPLETE: Found {final_total - initial_count} products in {category_name}")
            except Exception as e:
                print(f"Error in final processing: {e}")

            self.save_category_results(category_name)

        except Exception as e:
            print(f"✗ Error scraping {category_name}: {e}")

    def save_category_results(self, category_name):
        if not self.products:
            print(f"No products to save for {category_name}")
            return

        category_products = [p for p in self.products if p['category'] == category_name]

        if not category_products:
            print(f"No products found for {category_name}")
            return

        df = pd.DataFrame(category_products)
        df = df.drop_duplicates(subset=['name', 'price'])

        safe_filename = re.sub(r'[^\w\-_\.]', '_', category_name.lower())
        category_file = f"voila_{safe_filename}.csv"
        df.to_csv(category_file, index=False)

        print(f"✅ Saved {len(df)} products from {category_name} to {category_file}")

        all_df = pd.DataFrame(self.products)
        all_df = all_df.drop_duplicates(subset=['name', 'price', 'category'])
        all_df.to_csv("voila_focused_groceries_progress.csv", index=False)

        if 'price' in all_df.columns and all_df['price'].notna().any():
            valid_prices = all_df[all_df['price'].notna()]
            budget_items = valid_prices[valid_prices['price'] <= 5.0]
            if len(budget_items) > 0:
                budget_items.to_csv("voila_budget_items_progress.csv", index=False)

        print(f"📊 Total products so far: {len(all_df)} across {len(all_df['category'].unique())} categories")

    def scrape_all_target_categories(self, categories_to_scrape=None):
        if categories_to_scrape is None:
            categories_to_scrape = list(self.target_categories.keys())

        if not categories_to_scrape:
            print("No categories to scrape!")
            return

        print(f"\nStarting focused Voila grocery scraper...")
        print(f"Categories to scrape: {categories_to_scrape}")

        for category_name in categories_to_scrape:
            if category_name in self.target_categories:
                category_url = self.target_categories[category_name]
                self.scrape_category(category_name, category_url)
                time.sleep(2)
            else:
                print(f"⚠️  Unknown category: {category_name}")

    def save_results(self):
        if not self.products:
            print("No products found to save!")
            return

        df = pd.DataFrame(self.products)
        df = df.drop_duplicates(subset=['name', 'price', 'category'])

        df.to_csv("voila_focused_groceries_FINAL.csv", index=False)
        print(f"\n🎉 FINAL RESULTS: Saved {len(df)} products to voila_focused_groceries_FINAL.csv")

        print("\n📊 FINAL Category Summary:")
        category_counts = df['category'].value_counts()
        for category, count in category_counts.items():
            print(f"  {category}: {count} items")

        if 'price' in df.columns and df['price'].notna().any():
            valid_prices = df[df['price'].notna()]
            print(f"\n💰 FINAL Price Analysis:")
            print(f"  Total items with prices: {len(valid_prices)}")
            if len(valid_prices) > 0:
                print(f"  Price range: ${valid_prices['price'].min():.2f} - ${valid_prices['price'].max():.2f}")
                print(f"  Average price: ${valid_prices['price'].mean():.2f}")

                budget_items = valid_prices[valid_prices['price'] <= 5.0]
                if len(budget_items) > 0:
                    budget_items.to_csv("voila_budget_items_FINAL.csv", index=False)
                    print(f"  Budget items (≤$5): {len(budget_items)} saved to voila_budget_items_FINAL.csv")

        print(f"\n📁 Files created:")
        print(f"  - voila_focused_groceries_FINAL.csv (all {len(df)} products)")
        print(f"  - Individual category files for each section")
        print(f"  - voila_budget_items_FINAL.csv (budget items)")
        print(f"  - Progress files updated during scraping")

    def close(self):
        try:
            self.driver.quit()
        except:
            pass


def main():
    print("Voila Focused Grocery Scraper")
    print("Targeting specific categories for meal planning")
    print("=" * 50)

    scraper = VoilaFocusedScraper(headless=False)

    try:
        if scraper.is_auto_restart():
            print("🔄 AUTO-RESTART MODE DETECTED")
            categories_to_scrape = scraper.auto_continue_from_existing()
        else:
            print("👤 MANUAL START MODE")
            categories_to_scrape = scraper.handle_existing_files()

        if categories_to_scrape is None:
            scraper.close()
            return

        if not categories_to_scrape:
            print("\n🎉 All categories already scraped!")
            scraper.close()
            return

        print("\n" + "=" * 60)
        print("URL TESTING OPTION")
        print("=" * 60)
        print("Do you want to test category URLs before scraping?")
        print("This helps verify that all URLs are working correctly.")

        while True:
            test_choice = input("\nTest URLs? (y/n): ").strip().lower()
            if test_choice in ['y', 'yes']:
                test_urls = True
                break
            elif test_choice in ['n', 'no']:
                test_urls = False
                break
            else:
                print("Please enter 'y' for yes or 'n' for no.")

        if test_urls:
            print("\n" + "=" * 60)
            print("TESTING CATEGORY URLS TO SCRAPE")
            print("=" * 60)

            for category_name in categories_to_scrape:
                if category_name in scraper.target_categories:
                    category_url = scraper.target_categories[category_name]
                    print(f"Testing: {category_name}")
                    try:
                        scraper.driver.get(category_url)
                        time.sleep(2)

                        page_title = scraper.driver.title

                        if ("404" in page_title or "not found" in page_title.lower() or
                                "error" in page_title.lower()):
                            print(f"  ✗ {category_name} has issues: {page_title}")
                        elif category_name.lower() not in page_title.lower():
                            print(f"  ⚠️  {category_name} URL mismatch: {page_title}")
                        else:
                            print(f"  ✓ {category_name} loaded correctly")

                    except Exception as e:
                        print(f"  ✗ {category_name} failed to load: {e}")

        scraper.scrape_all_target_categories(categories_to_scrape)
        scraper.save_results()

        if scraper.products:
            print(f"\n🎉 Successfully scraped {len(scraper.products)} total products!")
            print("Files created:")
            print("  - voila_focused_groceries_FINAL.csv (all products)")
            print("  - voila_budget_items_FINAL.csv (budget items)")
            print("  - Individual category CSV files")
        else:
            print("\n⚠️  No products were found.")

    except KeyboardInterrupt:
        print("\n\n⚠️  SCRAPING INTERRUPTED BY USER")
        print("Progress has been saved. You can restart to continue from where you left off.")

    except Exception as e:
        print(f"\n💥 UNEXPECTED ERROR: {e}")

    finally:
        try:
            scraper.close()
        except:
            pass
        print("\nScript execution completed!")


if __name__ == "__main__":
    main()
