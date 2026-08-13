import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

interface Course {
  id: number
  name: string
  description: string | null
  created_at: string
}

export default function Dashboard() {
  const { data: courses, isLoading } = useQuery<Course[]>({
    queryKey: ['courses'],
    queryFn: async () => {
      const response = await axios.get('/api/v1/courses/')
      return response.data
    },
  })

  return (
    <div>
      <h2>Dashboard</h2>
      <div className="card" style={{ marginTop: '1rem' }}>
        <h3>Recent Courses</h3>
        {isLoading ? (
          <p>Loading...</p>
        ) : courses && courses.length > 0 ? (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {courses.map((course) => (
                <tr key={course.id}>
                  <td>{course.name}</td>
                  <td>{course.description || '-'}</td>
                  <td>{new Date(course.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>No courses yet. Create your first course to get started.</p>
        )}
      </div>
      
      <div className="card" style={{ marginTop: '1rem' }}>
        <h3>Quick Start Guide</h3>
        <ol style={{ marginLeft: '1.5rem', marginTop: '0.5rem' }}>
          <li>Create a course with student information</li>
          <li>Import audio recordings from class sessions</li>
          <li>Review transcripts and speaker assignments</li>
          <li>Analyze fluency metrics and disfluency patterns</li>
          <li>Generate CEFR-aligned evidence reports</li>
        </ol>
      </div>
    </div>
  )
}
