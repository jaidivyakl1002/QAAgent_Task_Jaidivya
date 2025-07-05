import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PlaywrightTestGenerator:
    """Converts JSON test cases to Playwright test scripts"""
    
    def __init__(self, base_url: str = "https://www.recruter.ai"):
        self.base_url = base_url
        self.test_template = self._load_template()
        
    def _load_template(self) -> str:
        """Base Playwright test template"""
        return '''// Auto-generated Playwright test
// Generated on: {timestamp}
// Test ID: {test_id}

import {{ test, expect, Page, BrowserContext }} from '@playwright/test';
import { loginToRecruterAi } from './auth-helper.js';

test.describe('{test_title}', () => {{
    let page: Page;
    let context: BrowserContext;

    test.beforeEach(async ({{ browser }}) => {{
        context = await browser.newContext({{
            viewport: {{ width: 1920, height: 1080 }},
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }});
        page = await context.newPage();
        
        // Set up error handling
        page.on('pageerror', (error) => {{
            console.error('Page error:', error);
        }});
        
        page.on('requestfailed', (request) => {{
            console.log('Failed request:', request.url());
        }});
    }});

    test.afterEach(async () => {{
        await context.close();
    }});

    test('{test_description}', async () => {{
        {test_steps}
    }});
}});
'''

    def generate_test_script(self, test_case: Dict[str, Any]) -> str:
        """Generate a complete Playwright test script from JSON test case"""
        try:
            # Extract test case details
            test_id = test_case.get('id', 'unknown')
            test_title = test_case.get('title', 'Untitled Test')
            test_description = test_case.get('description', 'No description')
            test_type = test_case.get('test_type', 'functional')
            steps = test_case.get('steps', [])
            
            # Generate test steps
            playwright_steps = self._generate_test_steps(steps, test_type)
            
            # Fill template
            script = self.test_template.format(
                timestamp=datetime.now().isoformat(),
                test_id=test_id,
                test_title=test_title,
                test_description=test_description,
                test_steps=playwright_steps
            )
            
            return script
            
        except Exception as e:
            logger.error(f"Error generating test script: {e}")
            return self._generate_error_script(test_case, str(e))
    
    def _generate_test_steps(self, steps: List[Dict], test_type: str) -> str:
        """Convert JSON steps to Playwright code"""
        playwright_code = []
        
        # Add initial navigation
        playwright_code.append(f"        // Navigate to base URL")
        playwright_code.append(f"        await page.goto('{self.base_url}');")
        playwright_code.append(f"        await page.waitForLoadState('networkidle');")
        playwright_code.append("")
        
        for i, step in enumerate(steps, 1):
            action = step.get('action', '').lower()
            selector = step.get('selector', '')
            value = step.get('value', '')
            expected_result = step.get('expected_result', '')
            wait_condition = step.get('wait_condition')
            screenshot = step.get('screenshot', False)
            
            playwright_code.append(f"        // Step {i}: {action}")
            
            # Generate code based on action type
            if action == 'navigate':
                url = value or selector
                playwright_code.append(f"        await page.goto('{url}');")
                playwright_code.append(f"        await page.waitForLoadState('networkidle');")
                
            elif action == 'click':
                playwright_code.append(f"        await page.click('{selector}');")
                if wait_condition:
                    playwright_code.append(f"        await page.waitForSelector('{wait_condition}');")
                
            elif action == 'fill' or action == 'type':
                playwright_code.append(f"        await page.fill('{selector}', '{value}');")
                
            elif action == 'verify_text':
                playwright_code.append(f"        await expect(page.locator('{selector}')).toContainText('{value}');")
                
            elif action == 'verify_visible':
                playwright_code.append(f"        await expect(page.locator('{selector}')).toBeVisible();")
                
            elif action == 'verify_enabled':
                playwright_code.append(f"        await expect(page.locator('{selector}')).toBeEnabled();")
                
            elif action == 'verify_aria':
                playwright_code.append(f"        // Accessibility check for ARIA labels")
                playwright_code.append(f"        const elements = await page.locator('{selector}').all();")
                playwright_code.append(f"        for (const element of elements) {{")
                playwright_code.append(f"            const ariaLabel = await element.getAttribute('aria-label');")
                playwright_code.append(f"            const ariaLabelledby = await element.getAttribute('aria-labelledby');")
                playwright_code.append(f"            expect(ariaLabel || ariaLabelledby).toBeTruthy();")
                playwright_code.append(f"        }}")
                
            elif action == 'wait':
                wait_time = int(value) if value else 1000
                playwright_code.append(f"        await page.waitForTimeout({wait_time});")
                
            elif action == 'hover':
                playwright_code.append(f"        await page.hover('{selector}');")
                
            elif action == 'select':
                playwright_code.append(f"        await page.selectOption('{selector}', '{value}');")
                
            elif action == 'verify_url':
                playwright_code.append(f"        expect(page.url()).toContain('{value}');")
                
            elif action == 'verify_title':
                playwright_code.append(f"        await expect(page).toHaveTitle(new RegExp('{value}', 'i'));")
                
            elif action == 'upload_file':
                playwright_code.append(f"        await page.setInputFiles('{selector}', '{value}');")
                
            elif action == 'verify_performance':
                playwright_code.append(f"        // Performance check")
                playwright_code.append(f"        const startTime = Date.now();")
                playwright_code.append(f"        await page.goto('{self.base_url}');")
                playwright_code.append(f"        await page.waitForLoadState('networkidle');")
                playwright_code.append(f"        const loadTime = Date.now() - startTime;")
                playwright_code.append(f"        expect(loadTime).toBeLessThan(3000); // 3 seconds")
                
            else:
                # Generic action
                playwright_code.append(f"        // Custom action: {action}")
                if selector:
                    playwright_code.append(f"        await page.locator('{selector}').click();")
            
            # Add screenshot if requested
            if screenshot:
                playwright_code.append(f"        await page.screenshot({{ path: 'screenshots/step_{i}_{test_type}.png' }});")
            
            # Add expected result as comment
            if expected_result:
                playwright_code.append(f"        // Expected: {expected_result}")
            
            playwright_code.append("")
        
        return "\n".join(playwright_code)
    
    def _generate_error_script(self, test_case: Dict, error: str) -> str:
        """Generate error test script when conversion fails"""
        return f'''// ERROR: Failed to generate test script
// Test ID: {test_case.get('id', 'unknown')}
// Error: {error}

import {{ test, expect }} from '@playwright/test';

test.describe('Error Test - {test_case.get('title', 'Unknown')}', () => {{
    test('Generation failed', async ({{ page }}) => {{
        // This test failed to generate due to: {error}
        console.log('Test case data:', {json.dumps(test_case, indent=2)});
        expect(false).toBeTruthy(); // This test will fail
    }});
}});
'''

    def generate_test_suite(self, test_cases: List[Dict[str, Any]], output_dir: str) -> Dict[str, Any]:
        """Generate multiple test scripts and organize them"""
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
                    
                except Exception as e:
                    logger.error(f"Failed to generate test {test_case.get('id', 'unknown')}: {e}")
                    generation_stats['failed'] += 1
            
            # Generate package.json and playwright.config.ts
            self._generate_config_files(output_path)
            
            # Generate test runner script
            self._generate_test_runner(output_path, generated_files)
            
            return {
                'output_directory': str(output_path),
                'generated_files': generated_files,
                'stats': generation_stats,
                'config_files': [
                    str(output_path / 'package.json'),
                    str(output_path / 'playwright.config.ts'),
                    str(output_path / 'run_tests.js')
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating test suite: {e}")
            return {
                'error': str(e),
                'generated_files': [],
                'stats': {'total_tests': 0, 'successful': 0, 'failed': len(test_cases)}
            }
    
    def _generate_config_files(self, output_path: Path):
        """Generate package.json and playwright.config.ts"""
        
        # package.json
        package_json = {
            "name": "recruter-ai-tests",
            "version": "1.0.0",
            "description": "Auto-generated Playwright tests for Recruter.ai",
            "scripts": {
                "test": "playwright test",
                "test:headed": "playwright test --headed",
                "test:debug": "playwright test --debug",
                "test:report": "playwright show-report",
                "install-deps": "npx playwright install"
            },
            "devDependencies": {
                "@playwright/test": "^1.40.0",
                "typescript": "^5.0.0"
            }
        }
        
        with open(output_path / 'package.json', 'w', encoding='utf-8') as f:
            json.dump(package_json, f, indent=2)
        
        # playwright.config.ts
        config_ts = '''import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results.json' }],
    ['junit', { outputFile: 'test-results.xml' }]
  ],
  use: {
    baseURL: 'https://www.recruter.ai',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    headless: true,
    viewport: { width: 1920, height: 1080 },
    ignoreHTTPSErrors: true,
    actionTimeout: 30000,
    navigationTimeout: 30000,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 12'] },
    },
  ],
  webServer: {
    command: 'echo "No local server needed"',
    reuseExistingServer: true,
  },
});
'''
        
        with open(output_path / 'playwright.config.ts', 'w', encoding='utf-8') as f:
            f.write(config_ts)
    
    def _generate_test_runner(self, output_path: Path, generated_files: List[Dict]):
        """Generate a test runner script"""
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