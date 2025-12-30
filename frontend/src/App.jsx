import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import theme from './theme/theme';
import { AuthProvider } from './context/AuthContext';
import { OrganizationProvider } from './context/OrganizationContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import ForceChangePasswordDialog from './components/ForceChangePasswordDialog';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import ProjectDetails from './pages/ProjectDetails';
import ProjectEdit from './pages/ProjectEdit';
import TestCaseEditor from './pages/TestCaseEditor';
import ProjectRunTests from './pages/ProjectRunTests';
import Reports from './pages/Reports';
import ReportDetail from './pages/ReportDetail';

import Releases from './pages/Releases';
import ReleaseDashboard from './pages/ReleaseDashboard';
import ReleaseEdit from './pages/ReleaseEdit';
import AITestGenerator from './pages/AITestGenerator';
import UnifiedTestRunner from './components/UnifiedTestRunner';
import UserManagement from './pages/UserManagement';
import TestCategoryView from './pages/TestCategoryView';
import Landing from './pages/Landing';
import HowItWorks from './pages/HowItWorks';
import TestLab from './pages/TestLab';
import Settings from './pages/Settings';
import Register from './pages/Register';
import Organizations from './pages/Organizations';

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <ForceChangePasswordDialog />
        <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<Landing />} />
            <Route path="/how-it-works" element={<HowItWorks />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Protected routes - wrapped in Layout */}
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <OrganizationProvider>
                  <Layout>
                    <Routes>
                      <Route path="/dashboard" element={<Dashboard />} />
                      <Route path="/projects" element={<Projects />} />
                      <Route path="/projects/:id" element={<ProjectDetails />} />
                      <Route path="/projects/:id/edit" element={<ProjectEdit />} />
                      <Route path="/projects/:id/test-cases/new" element={<TestCaseEditor />} />
                      <Route path="/projects/:id/test-cases/:testCaseId/edit" element={<TestCaseEditor />} />
                      <Route path="/projects/:id/:category" element={<TestCategoryView />} />

                      {/* Admin-only routes */}
                      <Route
                        path="/projects/:id/run"
                        element={
                          <ProtectedRoute adminOnly>
                            <ProjectRunTests />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/run-tests"
                        element={
                          <ProtectedRoute adminOnly>
                            <UnifiedTestRunner />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/releases"
                        element={
                          <ProtectedRoute adminOnly>
                            <Releases />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/releases/:id"
                        element={
                          <ProtectedRoute adminOnly>
                            <ReleaseDashboard />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/releases/:id/edit"
                        element={
                          <ProtectedRoute adminOnly>
                            <ReleaseEdit />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/users"
                        element={
                          <ProtectedRoute adminOnly>
                            <UserManagement />
                          </ProtectedRoute>
                        }
                      />

                      {/* Reports - admin only */}
                      <Route
                        path="/reports"
                        element={
                          <ProtectedRoute adminOnly>
                            <Reports />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/reports/:id"
                        element={
                          <ProtectedRoute adminOnly>
                            <ReportDetail />
                          </ProtectedRoute>
                        }
                      />

                                            {/* Test Lab - available to both admin and user */}
                      <Route path="/test-lab" element={<TestLab />} />
                      
                      {/* Settings - admin only */}
                      <Route
                        path="/settings"
                        element={
                          <ProtectedRoute adminOnly>
                            <Settings />
                          </ProtectedRoute>
                        }
                      />
                      
                      {/* Organization - redirects to Settings */}
                      <Route
                        path="/organization"
                        element={<Navigate to="/settings" replace />}
                      />
                      
                      {/* Organizations Management - Super Admin only */}
                      <Route
                        path="/organizations"
                        element={
                          <ProtectedRoute adminOnly>
                            <Organizations />
                          </ProtectedRoute>
                        }
                      />

                      {/* Available to both admin and user */}
                      <Route path="/generate" element={<AITestGenerator />} />
                    </Routes>
                  </Layout>
                  </OrganizationProvider>
                </ProtectedRoute>
              }
            />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
