import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { Link } from 'react-router-dom'

interface Course {
  id: number
  name: string
  description: string | null
  created_at: string
  is_archived: boolean
}

interface Job {
  id: number
  session_id: number
  status: string
  stage: string
  created_at: string
}

export default function Dashboard() {
  const { data: courses, isLoading: coursesLoading } = useQuery<Course[]>({
    queryKey: ['courses'],
    queryFn: async () => {
      const response = await axios.get('/api/v1/courses/')
      return response.data
    },
  })

  const { data: jobs, isLoading: jobsLoading } = useQuery<Job[]>({
    queryKey: ['jobs'],
    queryFn: async () => {
      const response = await axios.get('/api/v1/jobs/')
      return response.data
    },
  })

  const activeJobs = jobs?.filter(j => j.status === 'running' || j.status === 'pending' || j.status === 'queued') || []
  const recentCourses = courses?.slice(0, 5) || []

  return (
    <div className="dashboard">
      <h2 className="page-title">LEAP-D Dashboard</h2>
      
      <div className="stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        <div className="card stat-card">
          <h4>Courses</h4>
          <p className="stat-value">{courses?.length || 0}</p>
        </div>
        <div className="card stat-card">
          <h4>Active Jobs</h4>
          <p className="stat-value">{activeJobs.length}</p>
        </div>
        <div className="card stat-card">
          <h4>Sessions</h4>
          <p className="stat-value">-</p>
        </div>
        <div className="card stat-card">
          <h4>Students</h4>
          <p className="stat-value">-</p>
        </div>
      </div>
      
      <div className="grid-2" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1.5rem' }}>
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3>Recent Courses</h3>
            <Link to="/courses" className="btn btn-sm">View All</Link>
          </div>
          {coursesLoading ? (
            <p className="loading">Loading...</p>
          ) : recentCourses.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {recentCourses.map((course) => (
                  <tr key={course.id}>
                    <td>
                      <Link to={`/courses/${course.id}`}>{course.name}</Link>
                    </td>
                    <td>
                      {course.is_archived ? (
                        <span className="badge badge-secondary">Archived</span>
                      ) : (
                        <span className="badge badge-success">Active</span>
                      )}
                    </td>
                    <td>{new Date(course.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty-state">
              <p>No courses yet.</p>
              <Link to="/courses/new" className="btn btn-primary">Create First Course</Link>
            </div>
          )}
        </div>
        
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3>Processing Jobs</h3>
            <Link to="/jobs" className="btn btn-sm">View All</Link>
          </div>
          {jobsLoading ? (
            <p className="loading">Loading...</p>
          ) : activeJobs.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>Session</th>
                  <th>Stage</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {activeJobs.slice(0, 5).map((job) => (
                  <tr key={job.id}>
                    <td>Session #{job.session_id}</td>
                    <td>
                      <span className="badge badge-info">{job.stage}</span>
                    </td>
                    <td>
                      <span className={`badge badge-${job.status === 'running' ? 'warning' : job.status === 'completed' ? 'success' : 'secondary'}`}>
                        {job.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty-state">
              <p>No active processing jobs.</p>
            </div>
          )}
        </div>
      </div>
      
      <div className="card" style={{ marginTop: '1.5rem' }}>
        <h3>Quick Start Guide</h3>
        <ol style={{ marginLeft: '1.5rem', marginTop: '0.5rem', lineHeight: '1.8' }}>
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
