import { Outlet, NavLink } from 'react-router-dom'
import { Home, Search, FileText, Briefcase, Sparkles, Zap } from 'lucide-react'
import Logo from '../assets/Logo'

const navItems = [
  { to: '/', icon: Home, label: '首页' },
  { to: '/crawler', icon: Search, label: '职位爬取' },
  { to: '/jobs', icon: Briefcase, label: '职位库' },
  { to: '/resume', icon: FileText, label: '简历管理' },
  { to: '/smart-match', icon: Zap, label: '智能匹配' },
  { to: '/match', icon: Sparkles, label: '手动匹配' },
]

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* 顶部导航 */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <NavLink to="/" className="flex items-center gap-3 group">
              <Logo size={36} className="group-hover:scale-105 transition-transform" />
              <span className="text-xl font-bold gradient-text">DeepCareer</span>
            </NavLink>
            
            {/* 导航链接 */}
            <nav className="hidden md:flex items-center gap-1">
              {navItems.map(({ to, icon: Icon, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200
                    ${isActive 
                      ? 'bg-primary-50 text-primary-600' 
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    }`
                  }
                >
                  <Icon size={18} />
                  {label}
                </NavLink>
              ))}
            </nav>

            {/* 移动端菜单按钮 */}
            <button className="md:hidden btn-ghost p-2">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        <Outlet />
      </main>

      {/* 底部 */}
      <footer className="border-t border-gray-100 bg-white/80 backdrop-blur-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between text-sm text-gray-500">
            <div className="flex items-center gap-2">
              <Logo size={24} />
              <span>DeepCareer © 2025</span>
            </div>
            <span>智能职位匹配系统</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
