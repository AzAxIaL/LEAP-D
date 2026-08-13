import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Courses from './pages/Courses';
import Students from './pages/Students';
import Sessions from './pages/Sessions';
import SessionReview from './pages/SessionReview';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-background">
        {/* Navigation Header */}
        <header className="border-b bg-card">
          <div className="container mx-auto px-4 py-3">
            <nav className="flex items-center justify-between">
              <div className="flex items-center gap-6">
                <Link to="/" className="text-xl font-bold text-primary">
                  LEAP-D
                </Link>
                <div className="hidden md:flex items-center gap-4">
                  <Link 
                    to="/dashboard" 
                    className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Dashboard
                  </Link>
                  <Link 
                    to="/courses" 
                    className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Courses
                  </Link>
                  <Link 
                    to="/students" 
                    className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Students
                  </Link>
                  <Link 
                    to="/sessions" 
                    className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Sessions
                  </Link>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground hidden sm:inline-block">
                  Evidence-Based Assessment
                </span>
              </div>
            </nav>
          </div>
        </header>

        {/* Main Content */}
        <main className="container mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/courses" element={<Courses />} />
            <Route path="/students" element={<Students />} />
            <Route path="/sessions" element={<Sessions />} />
            <Route path="/sessions/:sessionId/review" element={<SessionReview />} />
          </Routes>
        </main>

        {/* Footer */}
        <footer className="border-t mt-auto">
          <div className="container mx-auto px-4 py-4">
            <div className="flex flex-col sm:flex-row justify-between items-center gap-2 text-sm text-muted-foreground">
              <span>LEAP-D - For formative assessment only</span>
              <span>Not validated for high-stakes decisions</span>
            </div>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default App;
