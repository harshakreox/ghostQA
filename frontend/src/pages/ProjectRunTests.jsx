/**
 * Project-specific Run Tests Page
 *
 * Wrapper that extracts project ID from URL params
 * and passes it to the UnifiedTestRunner component.
 */

import { useParams } from 'react-router-dom';
import UnifiedTestRunner from '../components/UnifiedTestRunner';

export default function ProjectRunTests() {
  const { id } = useParams();

  return <UnifiedTestRunner projectId={id} />;
}
