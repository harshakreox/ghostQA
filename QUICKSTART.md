# Quick Start Guide

## Setup (One-time)

### 1. Setup Backend
```bash
./setup-backend.sh
```

This will:
- Create a Python virtual environment
- Install all Python dependencies
- Install Playwright browsers
- Create necessary data directories

### 2. Setup Frontend
```bash
./setup-frontend.sh
```

This will:
- Install all Node.js dependencies

## Running the Application

You need to run both the backend and frontend servers.

### Terminal 1 - Backend Server
```bash
./start-backend.sh
```

Backend will be available at: `http://localhost:8000`

### Terminal 2 - Frontend Server
```bash
./start-frontend.sh
```

Frontend will be available at: `http://localhost:3000`

## First Steps

1. Open your browser and go to `http://localhost:3000`
2. Create your first project
3. Add test cases to the project
4. Run your tests and view the reports!

## Example Test Case

Here's an example of a simple test case to get you started:

**Project**: Google Search Test
**Base URL**: https://www.google.com

**Test Case**: Search for "Playwright"

Actions:
1. **Navigate** to `/`
2. **Type** "Playwright" into selector `textarea[name="q"]` (CSS selector)
3. **Click** on selector `input[name="btnK"]` (CSS selector)
4. **Wait** for 2000ms
5. **Assert Text** "Playwright" is visible

## Selector Tips

### Common Selectors:
- **ID**: Use `#element-id`
- **Class**: Use `.class-name`
- **Name**: Use `[name="input-name"]`
- **Placeholder**: Use `[placeholder="Enter text"]`
- **Text**: Use the exact text content
- **CSS**: Use any valid CSS selector
- **XPath**: Use XPath expressions

### Best Practices:
1. Prefer ID selectors when available
2. Use data-testid attributes in your app
3. Avoid overly specific CSS selectors
4. Test your selectors in browser DevTools first

## Troubleshooting

### Backend won't start
- Make sure you activated the virtual environment
- Check if port 8000 is already in use
- Verify Python 3.8+ is installed

### Frontend won't start
- Make sure Node.js 16+ is installed
- Try deleting `node_modules` and running `npm install` again
- Check if port 3000 is already in use

### Tests fail to run
- Make sure Playwright browsers are installed: `playwright install chromium`
- Check if the base URL is correct
- Verify selectors are valid

### WebSocket connection fails
- Check if both backend and frontend are running
- Verify the proxy configuration in `vite.config.js`
- Check browser console for errors

## Manual Setup (Alternative)

If you prefer to set up manually:

### Backend:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt --break-system-packages
playwright install chromium
mkdir -p data/projects data/reports
cd app
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Next Steps

- Explore the Dashboard to see project statistics
- Create complex test workflows with multiple actions
- Use the DOM extractor's intelligent selector suggestions
- View detailed test reports with screenshots
- Run tests in headless mode for CI/CD integration

Enjoy automated testing! 🚀
