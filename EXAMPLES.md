# Example Test Cases

This file contains example test cases you can use to test the framework.

## Example 1: Google Search Test

**Project Configuration:**
- Name: Google Search Test
- Description: Test basic Google search functionality
- Base URL: https://www.google.com

**Test Case: Search for Playwright**

| Step | Action | Selector Type | Selector | Value | Description |
|------|--------|---------------|----------|-------|-------------|
| 1 | Navigate | - | / | / | Navigate to Google homepage |
| 2 | Wait | - | - | 1000 | Wait for page to load |
| 3 | Type | CSS | textarea[name="q"] | Playwright | Type search query |
| 4 | Click | CSS | input[name="btnK"] | - | Click search button |
| 5 | Wait | - | - | 2000 | Wait for results |
| 6 | Assert Visible | CSS | #search | - | Verify search results visible |

## Example 2: Form Submission Test

**Project Configuration:**
- Name: Form Testing
- Description: Test form interactions
- Base URL: https://www.w3schools.com

**Test Case: Fill Contact Form**

| Step | Action | Selector Type | Selector | Value | Description |
|------|--------|---------------|----------|-------|-------------|
| 1 | Navigate | - | /action_page.php | /action_page.php | Go to form page |
| 2 | Type | ID | fname | John | Enter first name |
| 3 | Type | ID | lname | Doe | Enter last name |
| 4 | Click | CSS | input[type="submit"] | - | Submit form |
| 5 | Wait | - | - | 1000 | Wait for response |

## Example 3: Navigation Test

**Project Configuration:**
- Name: Navigation Test
- Description: Test website navigation
- Base URL: https://www.wikipedia.org

**Test Case: Browse Wikipedia**

| Step | Action | Selector Type | Selector | Value | Description |
|------|--------|---------------|----------|-------|-------------|
| 1 | Navigate | - | / | / | Go to Wikipedia home |
| 2 | Click | Text | English | - | Click English link |
| 3 | Wait | - | - | 2000 | Wait for page load |
| 4 | Type | ID | searchInput | Automation | Search for automation |
| 5 | Click | CSS | button[type="submit"] | - | Submit search |
| 6 | Wait | - | - | 2000 | Wait for results |
| 7 | Screenshot | - | - | wikipedia-search.png | Take screenshot |

## Tips for Creating Test Cases

1. **Start Simple**: Begin with basic navigation and clicking
2. **Use Waits**: Add waits between actions for stability
3. **Verify Results**: Use assertions to verify expected outcomes
4. **Capture Evidence**: Use screenshots for important steps
5. **Descriptive Names**: Use clear descriptions for each action

## Common Patterns

### Login Flow
1. Navigate to login page
2. Type username
3. Type password
4. Click login button
5. Assert successful login (verify dashboard element)

### Form Validation
1. Navigate to form
2. Click submit without filling
3. Assert error messages visible
4. Fill required fields
5. Submit form
6. Assert success message

### Multi-step Workflow
1. Navigate to start page
2. Click "Next" button
3. Fill step 1 fields
4. Click "Next" button
5. Fill step 2 fields
6. Click "Submit"
7. Assert completion message

## Selector Best Practices

### Priority Order:
1. `data-testid` attributes (if available)
2. ID selectors (#elementId)
3. Name attributes ([name="elementName"])
4. CSS selectors (.class-name)
5. XPath (as last resort)

### Examples:
- **Good**: `#login-button`, `[data-testid="submit-btn"]`, `button.primary`
- **Avoid**: `div > div > div > button:nth-child(3)` (too fragile)

## Debugging Tips

1. **Run in headed mode first** - See what's happening in the browser
2. **Check selectors in DevTools** - Verify selectors before adding to test
3. **Add waits if flaky** - Some elements need time to appear
4. **Use screenshots** - Capture the state when tests fail
5. **Check logs** - Real-time logs show exactly what's happening
