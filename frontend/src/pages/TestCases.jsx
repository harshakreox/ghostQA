import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { TestTube, FolderOpen } from 'lucide-react';
import { getProjects } from '../services/api';

const TestCases = () => {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const data = await getProjects();
      setProjects(data);
    } catch (error) {
      console.error('Error loading projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const allTestCases = projects.flatMap((project) =>
    (project.test_cases || []).map((tc) => ({
      ...tc,
      projectId: project.id,
      projectName: project.name,
    }))
  );

  if (loading) {
    return <div className="text-center py-8">Loading test cases...</div>;
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">All Test Cases</h1>

      {allTestCases.length === 0 ? (
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <TestTube size={64} className="mx-auto text-gray-400 mb-4" />
          <h3 className="text-xl font-medium mb-2">No test cases yet</h3>
          <p className="text-gray-600 mb-4">
            Create a project and add test cases to get started
          </p>
          <Link
            to="/projects"
            className="inline-block bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
          >
            Go to Projects
          </Link>
        </div>
      ) : (
        <div className="space-y-6">
          {projects
            .filter((p) => p.test_cases && p.test_cases.length > 0)
            .map((project) => (
              <div key={project.id} className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center gap-3 mb-4">
                  <FolderOpen className="text-blue-600" size={24} />
                  <div>
                    <Link
                      to={`/projects/${project.id}`}
                      className="text-xl font-bold hover:text-blue-600"
                    >
                      {project.name}
                    </Link>
                    <p className="text-sm text-gray-600">
                      {project.test_cases.length} test case
                      {project.test_cases.length !== 1 ? 's' : ''}
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  {project.test_cases.map((testCase) => (
                    <Link
                      key={testCase.id}
                      to={`/projects/${project.id}`}
                      className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      <div>
                        <h3 className="font-medium">{testCase.name}</h3>
                        <p className="text-sm text-gray-600">
                          {testCase.description}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          {testCase.actions?.length || 0} actions
                        </p>
                      </div>
                      <TestTube className="text-gray-400" size={20} />
                    </Link>
                  ))}
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
};

export default TestCases;
