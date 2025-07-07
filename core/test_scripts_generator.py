import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PlaywrightTestGenerator:
    """Enhanced Playwright test generator with better error handling and debugging"""
    
    def __init__(self, base_url: str = "https://www.app.recruter.ai"):
        self.base_url = base_url
        self.test_template = self._load_template()
    
    def _escape_string(self, value: str) -> str:
        """Properly escape strings for JavaScript/TypeScript"""
        if not value:
            return ""
        
        # Replace single quotes with escaped single quotes
        value = value.replace("'", "\\'")
        # Replace double quotes with escaped double quotes  
        value = value.replace('"', '\\"')
        # Replace newlines
        value = value.replace('\n', '\\n')
        value = value.replace('\r', '\\r')
        # Replace backslashes
        value = value.replace('\\', '\\\\')
        
        return value
    
    def _escape_selector(self, selector: str) -> str:
        """Properly escape CSS selectors for Playwright"""
        if not selector:
            return ""
        
        # For selectors, we need to be more careful
        # Replace single quotes with double quotes in attribute selectors
        selector = re.sub(r"=\s*'([^']*)'", r'="\1"', selector)
        
        # If the selector contains double quotes, escape them
        selector = selector.replace('"', '\\"')
        
        return selector
    
    # Give email and password below in const email and password     
    def _load_template(self) -> str:
        """Enhanced Playwright test template with better error handling"""
        return '''// Auto-generated Playwright test
// Generated on: {timestamp}
// Test ID: {test_id}
// Test Type: {test_type}

import {{ test, expect, Page, BrowserContext }} from '@playwright/test';

// Inline login function to avoid import issues
async function loginToRecruterAi(page: Page): Promise<void> {{
    const email = '';
    const password = '';
    
    console.log('🔐 Navigating to login page...');
    await page.goto('https://www.app.recruter.ai/', {{ waitUntil: 'domcontentloaded', timeout: 15000 }});
    
    console.log('🔐 Filling login credentials...');
    // Fill email field
    await page.waitForSelector('input[name="email"]', {{ timeout: 10000 }});
    await page.fill('input[name="email"]', email);
    
    // Fill password field
    await page.waitForSelector('input[name="password"]', {{ timeout: 10000 }});
    await page.fill('input[name="password"]', password);
    
    console.log('🔐 Clicking sign in button...');
    // Click the sign in button
    await page.click('button[type="submit"]');
    
    // Wait for successful login (adjust the selector based on your dashboard)
    await page.waitForURL(/dashboard|home|profile/, {{ timeout: 15000 }});
    console.log('✅ Login successful');
}}

test.describe('{test_title}', () => {{
    let page: Page;
    let context: BrowserContext;

    test.beforeEach(async ({{ browser }}) => {{
        // Create context with enhanced debugging
        context = await browser.newContext({{
            viewport: {{ width: 1920, height: 1080 }},
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ignoreHTTPSErrors: true,
            permissions: ['notifications'],
            extraHTTPHeaders: {{
                'Accept-Language': 'en-US,en;q=0.9'
            }}
        }});
        
        page = await context.newPage();
        console.log('🔐 Logging into Recruter.ai');
        await loginToRecruterAi(page);
        console.log('✅ Login successful');
        
        // Enhanced error handling
        page.on('pageerror', (error) => {{
            console.error('🚨 Page JavaScript error:', error.message);
            console.error('Stack:', error.stack);
        }});
        
        page.on('requestfailed', (request) => {{
            console.log('⚠️  Failed request:', request.url());
            console.log('   Method:', request.method());
            console.log('   Failure:', request.failure()?.errorText);
        }});
        
        page.on('console', (msg) => {{
            if (msg.type() === 'error') {{
                console.log('🔍 Console error:', msg.text());
            }}
        }});
        
        // Set longer timeouts for debugging
        page.setDefaultTimeout(30000);
        page.setDefaultNavigationTimeout(30000);
    }});

    test.afterEach(async () => {{
        // Take screenshot on failure
        if (test.info().status === 'failed') {{
            await page.screenshot({{ 
                path: `screenshots/failed-${{test.info().title.replace(/[^a-zA-Z0-9]/g, '-')}}-${{Date.now()}}.png`,
                fullPage: true 
            }});
        }}
        await context.close();
    }});

    test('{test_description}', async () => {{
        try {{
            console.log('🚀 Starting test: {test_description}');
            {test_steps}
            console.log('✅ Test completed successfully');
        }} catch (error) {{
            console.error('❌ Test failed:', error.message);
            console.error('Current URL:', page.url());
            
            // Take debug screenshot
            await page.screenshot({{ 
                path: `screenshots/debug-${{test.info().title.replace(/[^a-zA-Z0-9]/g, '-')}}-${{Date.now()}}.png`,
                fullPage: true 
            }});
            
            throw error;
        }}
    }});
}});
'''

    def generate_test_script(self, test_case: Dict[str, Any]) -> str:
        """Generate a complete Playwright test script with enhanced error handling"""
        try:
            # Extract test case details
            test_id = test_case.get('id', 'unknown')
            test_title = test_case.get('title', 'Untitled Test')
            test_description = test_case.get('description', 'No description')
            test_type = test_case.get('test_type', 'functional')
            steps = test_case.get('steps', [])
            
            # Generate test steps with enhanced error handling
            playwright_steps = self._generate_test_steps(steps, test_type)
            
            # Fill template
            script = self.test_template.format(
                timestamp=datetime.now().isoformat(),
                test_id=test_id,
                test_title=test_title,
                test_description=test_description,
                test_type=test_type,
                test_steps=playwright_steps
            )
            
            return script
            
        except Exception as e:
            logger.error(f"Error generating test script: {e}")
            return self._generate_error_script(test_case, str(e))
    
    def _generate_test_steps(self, steps: List[Dict], test_type: str) -> str:
        """Convert JSON steps to Playwright code with robust error handling and proper escaping"""
        playwright_code = []
        
        # Add initial navigation with retry logic
        playwright_code.append(f"        // Navigate to login page first")
        playwright_code.append(f"        console.log('🌐 Navigating to: https://www.app.recruter.ai/');")
        playwright_code.append(f"        ")
        playwright_code.append(f"        let retries = 3;")
        playwright_code.append(f"        while (retries > 0) {{")
        playwright_code.append(f"            try {{")
        playwright_code.append(f"                await page.goto('https://www.app.recruter.ai/', {{ waitUntil: 'domcontentloaded', timeout: 30000 }});")
        playwright_code.append(f"                await page.waitForLoadState('networkidle', {{ timeout: 10000 }});")
        playwright_code.append(f"                console.log('✅ Login page loaded successfully');")
        playwright_code.append(f"                break;")
        playwright_code.append(f"            }} catch (navError) {{")
        playwright_code.append(f"                retries--;")
        playwright_code.append(f"                console.log(`⚠️  Navigation attempt failed, retries left: ${{retries}}`);")
        playwright_code.append(f"                if (retries === 0) {{")
        playwright_code.append(f"                    console.error('❌ Failed to load login page after 3 attempts');")
        playwright_code.append(f"                    throw navError;")
        playwright_code.append(f"                }}")
        playwright_code.append(f"                await page.waitForTimeout(2000);")
        playwright_code.append(f"            }}")
        playwright_code.append(f"        }}")
        playwright_code.append("")
        
        # Add page health check
        playwright_code.append(f"        // Check if page loaded correctly")
        playwright_code.append(f"        const pageTitle = await page.title();")
        playwright_code.append(f"        console.log('📄 Page title:', pageTitle);")
        playwright_code.append(f"        ")
        playwright_code.append(f"        // Wait for any loading indicators to disappear")
        playwright_code.append(f"        const loadingSelectors = [")
        playwright_code.append(f"            '[data-testid=\"loading\"]',")
        playwright_code.append(f"            '.loading',")
        playwright_code.append(f"            '.spinner',")
        playwright_code.append(f"            '[aria-label*=\"loading\"]'")
        playwright_code.append(f"        ];")
        playwright_code.append(f"        ")
        playwright_code.append(f"        for (const selector of loadingSelectors) {{")
        playwright_code.append(f"            try {{")
        playwright_code.append(f"                await page.waitForSelector(selector, {{ state: 'detached', timeout: 5000 }});")
        playwright_code.append(f"            }} catch (e) {{")
        playwright_code.append(f"                // Loading indicator not found or already gone")
        playwright_code.append(f"            }}")
        playwright_code.append(f"        }}")
        playwright_code.append("")

        # Generate test type specific setup
        if test_type == 'accessibility':
            playwright_code.append(f"        // Install axe-core for accessibility testing")
            playwright_code.append(f"        await page.addScriptTag({{ url: 'https://unpkg.com/axe-core@4.7.2/axe.min.js' }});")
            playwright_code.append("")
        elif test_type == 'performance':
            playwright_code.append(f"        // Start performance monitoring")
            playwright_code.append(f"        await page.addInitScript(() => {{")
            playwright_code.append(f"            window.performanceMetrics = [];")
            playwright_code.append(f"            const originalFetch = window.fetch;")
            playwright_code.append(f"            window.fetch = function(...args) {{")
            playwright_code.append(f"                const start = performance.now();")
            playwright_code.append(f"                return originalFetch.apply(this, args).then(response => {{")
            playwright_code.append(f"                    const end = performance.now();")
            playwright_code.append(f"                    window.performanceMetrics.push({{ url: args[0], duration: end - start }});")
            playwright_code.append(f"                    return response;")
            playwright_code.append(f"                }});")
            playwright_code.append(f"            }};")
            playwright_code.append(f"        }});")
            playwright_code.append("")

        # Process each step
        for i, step in enumerate(steps, 1):
            action = step.get('action', '').lower()
            selector = step.get('selector', '')
            value = step.get('value', '')
            expected_result = step.get('expected_result', '')
            wait_condition = step.get('wait_condition')
            screenshot = step.get('screenshot', False)
            
            # Properly escape values
            escaped_selector = self._escape_selector(selector)
            escaped_value = self._escape_string(value)
            escaped_expected = self._escape_string(expected_result)
            
            playwright_code.append(f"        // Step {i}: {action}")
            playwright_code.append(f"        console.log('🔄 Executing step {i}: {action}');")
            
            # Generate code based on action type with enhanced error handling
            if action == 'navigate':
                url = escaped_value or escaped_selector
                playwright_code.append(f"        try {{")
                playwright_code.append(f"            await page.goto('{url}', {{ waitUntil: 'domcontentloaded', timeout: 30000 }});")
                playwright_code.append(f"            await page.waitForLoadState('networkidle', {{ timeout: 10000 }});")
                playwright_code.append(f"            console.log('✅ Navigation successful');")
                playwright_code.append(f"        }} catch (error) {{")
                playwright_code.append(f"            console.error('❌ Navigation failed:', error.message);")
                playwright_code.append(f"            throw error;")
                playwright_code.append(f"        }}")
            
            elif action == 'login':
                playwright_code.append(f"        try {{")
                playwright_code.append(f"            // Fill email field")
                playwright_code.append(f"            await page.waitForSelector('input[name=\"email\"]', {{ state: 'visible', timeout: 10000 }});")
                playwright_code.append(f"            await page.fill('input[name=\"email\"]', 'jaidivya.lohani@learner.manipal.edu');")
                playwright_code.append(f"            ")
                playwright_code.append(f"            // Fill password field")
                playwright_code.append(f"            await page.waitForSelector('input[name=\"password\"]', {{ state: 'visible', timeout: 10000 }});")
                playwright_code.append(f"            await page.fill('input[name=\"password\"]', 'Screwdriver@1002');")
                playwright_code.append(f"            ")
                playwright_code.append(f"            // Click sign in button")
                playwright_code.append(f"            await page.click('button[type=\"submit\"]');")
                playwright_code.append(f"            ")
                playwright_code.append(f"            // Wait for successful login")
                playwright_code.append(f"            await page.waitForURL(/dashboard|home|profile/, {{ timeout: 15000 }});")
                playwright_code.append(f"            console.log('✅ Login successful');")
                playwright_code.append(f"        }} catch (error) {{")
                playwright_code.append(f"            console.error('❌ Login failed:', error.message);")
                playwright_code.append(f"            await page.screenshot({{ path: 'screenshots/login-failed.png', fullPage: true }});")
                playwright_code.append(f"            throw error;")
                playwright_code.append(f"        }}")

            elif action == 'click':
                playwright_code.append(f"        try {{")
                playwright_code.append(f"            // Wait for element to be clickable")
                playwright_code.append(f"            await page.waitForSelector('{escaped_selector}', {{ state: 'visible', timeout: 10000 }});")
                playwright_code.append(f"            await page.locator('{escaped_selector}').click({{ timeout: 5000 }});")
                playwright_code.append(f"            console.log('✅ Click successful');")
                
                if wait_condition:
                    escaped_wait_condition = self._escape_selector(wait_condition)
                    playwright_code.append(f"            await page.waitForSelector('{escaped_wait_condition}', {{ timeout: 10000 }});")
                    
                playwright_code.append(f"        }} catch (error) {{")
                playwright_code.append(f"            console.error('❌ Click failed on selector: {escaped_selector}');")
                playwright_code.append(f"            console.error('Error:', error.message);")
                playwright_code.append(f"            ")
                playwright_code.append(f"            // Try to find similar elements")
                playwright_code.append(f"            const elements = await page.locator('button, a, [role=\"button\"]').all();")
                playwright_code.append(f"            console.log(`Found ${{elements.length}} clickable elements on page`);")
                playwright_code.append(f"            throw error;")
                playwright_code.append(f"        }}")
                
            elif action == 'fill' or action == 'type':
                playwright_code.append(f"        try {{")
                playwright_code.append(f"            await page.waitForSelector('{escaped_selector}', {{ state: 'visible', timeout: 10000 }});")
                playwright_code.append(f"            await page.locator('{escaped_selector}').clear();")
                playwright_code.append(f"            await page.locator('{escaped_selector}').fill('{escaped_value}');")
                playwright_code.append(f"            console.log('✅ Fill successful');")
                playwright_code.append(f"        }} catch (error) {{")
                playwright_code.append(f"            console.error('❌ Fill failed on selector: {escaped_selector}');")
                playwright_code.append(f"            throw error;")
                playwright_code.append(f"        }}")
                
            elif action == 'verify_text':
                playwright_code.append(f"        try {{")
                playwright_code.append(f"            await page.waitForSelector('{escaped_selector}', {{ timeout: 10000 }});")
                playwright_code.append(f"            await expect(page.locator('{escaped_selector}')).toContainText('{escaped_value}', {{ timeout: 5000 }});")
                playwright_code.append(f"            console.log('✅ Text verification successful');")
                playwright_code.append(f"        }} catch (error) {{")
                playwright_code.append(f"            const actualText = await page.locator('{escaped_selector}').textContent().catch(() => 'Element not found');")
                playwright_code.append(f"            console.error('❌ Text verification failed');")
                playwright_code.append(f"            console.error('Expected:', '{escaped_value}');")
                playwright_code.append(f"            console.error('Actual:', actualText);")
                playwright_code.append(f"            throw error;")
                playwright_code.append(f"        }}")
                
            elif action == 'verify_visible':
                playwright_code.append(f"        try {{")
                playwright_code.append(f"            await expect(page.locator('{escaped_selector}')).toBeVisible({{ timeout: 10000 }});")
                playwright_code.append(f"            console.log('✅ Visibility verification successful');")
                playwright_code.append(f"        }} catch (error) {{")
                playwright_code.append(f"            console.error('❌ Element not visible: {escaped_selector}');")
                playwright_code.append(f"            throw error;")
                playwright_code.append(f"        }}")
                
            elif action == 'verify_accessibility':
                playwright_code.append(f"        try {{")
                playwright_code.append(f"            // Run axe accessibility scan")
                playwright_code.append(f"            const axeResults = await page.evaluate(() => {{")
                playwright_code.append(f"                return new Promise((resolve) => {{")
                playwright_code.append(f"                    if (typeof axe !== 'undefined') {{")
                playwright_code.append(f"                        axe.run(document, (err, results) => {{")
                playwright_code.append(f"                            resolve(results);")
                playwright_code.append(f"                        }});")
                playwright_code.append(f"                    }} else {{")
                playwright_code.append(f"                        resolve({{ violations: [] }});")
                playwright_code.append(f"                    }}")
                playwright_code.append(f"                }});")
                playwright_code.append(f"            }});")
                playwright_code.append(f"            ")
                playwright_code.append(f"            console.log(`🔍 Accessibility scan completed. Found ${{axeResults.violations?.length || 0}} violations`);")
                playwright_code.append(f"            ")
                playwright_code.append(f"            if (axeResults.violations && axeResults.violations.length > 0) {{")
                playwright_code.append(f"                console.error('❌ Accessibility violations found:');")
                playwright_code.append(f"                axeResults.violations.forEach(violation => {{")
                playwright_code.append(f"                    console.error(`- ${{violation.id}}: ${{violation.description}}`);")
                playwright_code.append(f"                }});")
                playwright_code.append(f"            }}")
                playwright_code.append(f"            ")
                playwright_code.append(f"            expect(axeResults.violations?.length || 0).toBe(0);")
                playwright_code.append(f"            console.log('✅ Accessibility verification successful');")
                playwright_code.append(f"        }} catch (error) {{")
                playwright_code.append(f"            console.error('❌ Accessibility check failed:', error.message);")
                playwright_code.append(f"            throw error;")
                playwright_code.append(f"        }}")
                
            elif action == 'verify_performance':
                playwright_code.append(f"        try {{")
                playwright_code.append(f"            // Check page load performance")
                playwright_code.append(f"            const performanceData = await page.evaluate(() => {{")
                playwright_code.append(f"                const perfData = performance.getEntriesByType('navigation')[0];")
                playwright_code.append(f"                return {{")
                playwright_code.append(f"                    loadTime: perfData.loadEventEnd - perfData.loadEventStart,")
                playwright_code.append(f"                    domContentLoaded: perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart,")
                playwright_code.append(f"                    firstPaint: performance.getEntriesByType('paint').find(p => p.name === 'first-paint')?.startTime || 0")
                playwright_code.append(f"                }};")
                playwright_code.append(f"            }});")
                playwright_code.append(f"            ")
                playwright_code.append(f"            console.log('📊 Performance metrics:', performanceData);")
                playwright_code.append(f"            ")
                playwright_code.append(f"            // Check thresholds")
                playwright_code.append(f"            expect(performanceData.loadTime).toBeLessThan(5000); // 5 seconds")
                playwright_code.append(f"            expect(performanceData.domContentLoaded).toBeLessThan(3000); // 3 seconds")
                playwright_code.append(f"            console.log('✅ Performance verification successful');")
                playwright_code.append(f"        }} catch (error) {{")
                playwright_code.append(f"            console.error('❌ Performance check failed:', error.message);")
                playwright_code.append(f"            throw error;")
                playwright_code.append(f"        }}")
                
            elif action == 'wait':
                wait_time = int(value) if value and value.isdigit() else 1000
                playwright_code.append(f"        await page.waitForTimeout({wait_time});")
                
            else:
                # Generic action with better error handling
                playwright_code.append(f"        try {{")
                playwright_code.append(f"            // Custom action: {action}")
                if selector:
                    playwright_code.append(f"            await page.waitForSelector('{escaped_selector}', {{ timeout: 10000 }});")
                    playwright_code.append(f"            await page.locator('{escaped_selector}').click();")
                playwright_code.append(f"            console.log('✅ Custom action successful');")
                playwright_code.append(f"        }} catch (error) {{")
                playwright_code.append(f"            console.error('❌ Custom action failed:', error.message);")
                playwright_code.append(f"            throw error;")
                playwright_code.append(f"        }}")
            
            # Add screenshot if requested
            if screenshot:
                playwright_code.append(f"        // Take screenshot")
                playwright_code.append(f"        await page.screenshot({{ path: 'screenshots/step_{i}_{test_type}.png', fullPage: true }});")
            
            # Add expected result as comment
            if expected_result:
                playwright_code.append(f"        // Expected: {escaped_expected}")
            
            playwright_code.append("")
        
        return "\n".join(playwright_code)
    
    def _generate_error_script(self, test_case: Dict, error: str) -> str:
        """Generate error test script when conversion fails"""
        return f'''// ERROR: Failed to generate test script
// Test ID: {test_case.get('id', 'unknown')}
// Error: {error}
// Generated: {datetime.now().isoformat()}

import {{ test, expect }} from '@playwright/test';

test.describe('Error Test - {test_case.get('title', 'Unknown')}', () => {{
    test('Generation failed - {test_case.get('id', 'unknown')}', async ({{ page }}) => {{
        console.error('❌ This test failed to generate due to:', '{error}');
        console.log('📋 Test case data:', {json.dumps(test_case, indent=2)});
        
        // Try basic navigation to see if the issue is with the site
        try {{
            await page.goto('https://www.recruter.ai', {{ timeout: 30000 }});
            console.log('✅ Basic navigation works');
        }} catch (navError) {{
            console.error('❌ Even basic navigation failed:', navError.message);
        }}
        
        // This test will fail to indicate the generation issue
        expect(false, 'Test generation failed: {error}').toBeTruthy();
    }});
}});
'''

    def _generate_config_files(self, output_path: Path):
        """Generate enhanced package.json and playwright.config.ts with debugging"""
        
        # Enhanced package.json
        package_json = {
            "name": "recruter-ai-tests",
            "version": "1.0.0",
            "description": "Auto-generated Playwright tests for Recruter.ai",
            "scripts": {
                "test": "playwright test",
                "test:headed": "playwright test --headed",
                "test:debug": "playwright test --debug",
                "test:report": "playwright show-report",
                "test:ui": "playwright test --ui",
                "install-deps": "npx playwright install",
                "test:chrome": "playwright test --project=chromium",
                "test:slow": "playwright test --timeout=60000",
                "test:trace": "playwright test --trace=on"
            },
            "devDependencies": {
                "@playwright/test": "^1.40.0",
                "typescript": "^5.0.0",
                "@types/node": "^20.0.0"
            }
        }
        
        with open(output_path / 'package.json', 'w', encoding='utf-8') as f:
            json.dump(package_json, f, indent=2)
        
        # Enhanced playwright.config.ts
        config_ts = '''import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './',
  fullyParallel: false, // Run tests sequentially for better debugging
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: process.env.CI ? 1 : 1, // Single worker for debugging
  timeout: 60000, // 60 seconds timeout
  expect: {
    timeout: 10000, // 10 seconds for assertions
  },
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['json', { outputFile: 'test-results.json' }],
    ['junit', { outputFile: 'test-results.xml' }],
    ['list'] // Console output
  ],
  use: {
    baseURL: process.env.BASE_URL || 'https://www.recruter.ai',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    headless: process.env.HEADLESS !== 'false', // Default to headless
    viewport: { width: 1920, height: 1080 },
    ignoreHTTPSErrors: true,
    actionTimeout: 15000,
    navigationTimeout: 30000,
    launchOptions: {
      args: [
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-extensions',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding'
      ]
    }
  },
  projects: [
    {
      name: 'chromium-debug',
      use: { 
        ...devices['Desktop Chrome'],
        headless: false,
        slowMo: 100 // Slow down actions for debugging
      },
    },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Uncomment for cross-browser testing
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],
  
  // Global setup
  globalSetup: require.resolve('./global-setup.js'),
  
  // Output directories
  outputDir: 'test-results/',
});
'''
        
        with open(output_path / 'playwright.config.ts', 'w', encoding='utf-8') as f:
            f.write(config_ts)
        
        # Create global setup file
        global_setup = '''// global-setup.js
const { chromium } = require('@playwright/test');
const fs = require('fs');

module.exports = async () => {
  console.log('🔧 Global setup starting...');
  
  // Create directories
  const dirs = ['screenshots', 'test-results', 'playwright-report'];
  dirs.forEach(dir => {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
      console.log(`📁 Created directory: ${dir}`);
    }
  });
  
  // Test basic connectivity
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  try {
    console.log('🌐 Testing connectivity to recruter.ai...');
    await page.goto('https://www.app.recruter.ai/', { timeout: 30000 });
    console.log('✅ Basic connectivity test passed');
} catch (error) {
    console.error('❌ Basic connectivity test failed:', error.message);
    console.log('⚠️  This may cause tests to fail');
}
  
  console.log('🔧 Global setup completed');
};
'''
        
        with open(output_path / 'global-setup.js', 'w', encoding='utf-8') as f:
            f.write(global_setup)

    def generate_test_suite(self, test_cases: List[Dict[str, Any]], output_dir: str) -> Dict[str, Any]:
        """Generate multiple test scripts with enhanced debugging"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Create directories for different test types
            test_types = set()
            for test_case in test_cases:
                test_types.add(test_case.get('test_type', 'functional'))
            
            for test_type in test_types:
                (output_path / test_type).mkdir(parents=True, exist_ok=True)
            
            generated_files = []
            generation_stats = {
                'total_tests': len(test_cases),
                'successful': 0,
                'failed': 0,
                'by_type': {}
            }
            
            # Generate individual test scripts
            for test_case in test_cases:
                try:
                    test_id = test_case.get('id', f'test_{len(generated_files)}')
                    test_type = test_case.get('test_type', 'functional')
                    
                    # Generate script
                    script = self.generate_test_script(test_case)
                    
                    # Save to file
                    filename = f"{test_id}.spec.ts"
                    file_path = output_path / test_type / filename
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(script)
                    
                    generated_files.append({
                        'test_id': test_id,
                        'test_type': test_type,
                        'file_path': str(file_path),
                        'title': test_case.get('title', 'Untitled')
                    })
                    
                    generation_stats['successful'] += 1
                    generation_stats['by_type'][test_type] = generation_stats['by_type'].get(test_type, 0) + 1
                    
                    logger.info(f"Generated test script: {filename}")
                    
                except Exception as e:
                    logger.error(f"Failed to generate test {test_case.get('id', 'unknown')}: {e}")
                    generation_stats['failed'] += 1
            
            # Generate configuration files
            self._generate_config_files(output_path)
            
            # Generate enhanced test runner
            self._generate_test_runner(output_path, generated_files)
            
            return {
                'output_directory': str(output_path),
                'generated_files': generated_files,
                'stats': generation_stats,
                'config_files': [
                    str(output_path / 'package.json'),
                    str(output_path / 'playwright.config.ts'),
                    str(output_path / 'global-setup.js'),
                    str(output_path / 'run_tests.js')
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating test suite: {e}")
            return {
                'error': str(e),
                'generated_files': [],
                'stats': {'total_tests': 0, 'successful': 0, 'failed': len(test_cases) if test_cases else 0}
            }
    
    def _generate_test_runner(self, output_path: Path, generated_files: List[Dict]):
        """Generate enhanced test runner with debugging capabilities"""
        runner_script = '''const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

console.log('🎭 Recruter.ai Test Suite Runner');
console.log('================================');

// Install dependencies if needed
try {
    console.log('📦 Installing Playwright...');
    execSync('npm install', { stdio: 'inherit' });
    execSync('npx playwright install', { stdio: 'inherit' });
    console.log('✅ Dependencies installed');
} catch (error) {
    console.error('❌ Failed to install dependencies:', error.message);
    process.exit(1);
}

// Create screenshots directory
const screenshotsDir = path.join(__dirname, 'screenshots');
if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir, { recursive: true });
}

// Run tests
try {
    console.log('🚀 Running tests...');
    
    // Run all tests
    execSync('npx playwright test', { stdio: 'inherit' });
    
    console.log('✅ Tests completed successfully!');
    console.log('📊 View report: npx playwright show-report');
    
} catch (error) {
    console.error('❌ Tests failed:', error.message);
    console.log('📊 View report: npx playwright show-report');
    process.exit(1);
}
'''
        
        with open(output_path / 'run_tests.js', 'w', encoding='utf-8') as f:
            f.write(runner_script)
        
        # Make it executable
        os.chmod(output_path / 'run_tests.js', 0o755)