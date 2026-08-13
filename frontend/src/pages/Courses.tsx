import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { Link } from 'react-router-dom'

interface Course {
  id: number
  name: string
  description: string | null
  created_at: string
  is_archived: boolean
  retention_days: number
}

export default function Courses() {
  const [showNewForm, setShowNewForm] = useState(false)
  const [newCourse, setNewCourse] = useState({ name: '', description: '', retention_days: 365 })
  const queryClient = useQueryClient()

  const { data: courses, isLoading } = useQuery<Course[]>({
    queryKey: ['courses'],
    queryFn: async () => {
      const response = await axios.get('/api/v1/courses/')
      return response.data
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: typeof newCourse) => axios.post('/api/v1/courses/', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['courses'] })
      setShowNewForm(false)
      setNewCourse({ name: '', description: '', retention_days: 365 })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate(newCourse)
  }

  return (
    <div className="courses-page">
      <div className="page-header">
        <h2 className="page-title">Courses</h2>
        <button 
          className="btn btn-primary" 
          onClick={() => setShowNewForm(!showNewForm)}
        >
          {showNewForm ? 'Cancel' : '+ New Course'}
        </button>
      </div>

      {showNewForm && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <h3>Create New Course</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="name">Course Name *</label>
              <input
                id="name"
                type="text"
                required
                value={newCourse.name}
                onChange={(e) => setNewCourse({ ...newCourse, name: e.target.value })}
                placeholder="e.g., Advanced English Conversation"
              />
            </div>
            <div className="form-group">
              <label htmlFor="description">Description</label>
              <textarea
                id="description"
                value={newCourse.description}
                onChange={(e) => setNewCourse({ ...newCourse, description: e.target.value })}
                placeholder="Optional course description"
                rows={3}
              />
            </div>
            <div className="form-group">
              <label htmlFor="retention">Retention Period (days)</label>
              <input
                id="retention"
                type="number"
                min="30"
                max="730"
                value={newCourse.retention_days}
                onChange={(e) => setNewCourse({ ...newCourse, retention_days: parseInt(e.target.value) || 365 })}
              />
              <small>Data will be automatically deleted after this period</small>
            </div>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Creating...' : 'Create Course'}
              </button>
            </div>
          </form>
        </div>
      )}

      {isLoading ? (
        <p className="loading">Loading courses...</p>
      ) : courses && courses.length > 0 ? (
        <div className="card">
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Students</th>
                <th>Sessions</th>
                <th>Retention</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {courses.map((course) => (
                <tr key={course.id}>
                  <td>
                    <Link to={`/courses/${course.id}`}>{course.name}</Link>
                  </td>
                  <td>{course.description || '-'}</td>
                  <td>-</td>
                  <td>-</td>
                  <td>{course.retention_days} days</td>
                  <td>
                    {course.is_archived ? (
                      <span className="badge badge-secondary">Archived</span>
                    ) : (
                      <span className="badge badge-success">Active</span>
                    )}
                  </td>
                  <td>{new Date(course.created_at).toLocaleDateString()}</td>
                  <td>
                    <Link to={`/courses/${course.id}`} className="btn btn-sm">View</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="card empty-state">
          <p>No courses yet.</p>
          <button className="btn btn-primary" onClick={() => setShowNewForm(true)}>
            Create Your First Course
          </button>
        </div>
      )}
    </div>
  )
}
