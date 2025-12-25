import { Link } from 'react-router-dom'
import { useEffect } from 'react'
import { Search, FileText, Sparkles, ArrowRight, Briefcase, TrendingUp, Target } from 'lucide-react'
import Logo from '../assets/Logo'

const features = [
  {
    icon: Search,
    title: '智能爬取',
    desc: '自动爬取BOSS直聘等平台的最新职位信息',
    to: '/crawler',
    color: 'from-blue-500 to-cyan-500',
  },
  {
    icon: FileText,
    title: '简历解析',
    desc: '智能解析简历，提取关键信息并结构化存储',
    to: '/resume',
    color: 'from-emerald-500 to-teal-500',
  },
  {
    icon: Sparkles,
    title: 'AI匹配',
    desc: '基于7维度算法，精准匹配最适合你的职位',
    to: '/match',
    color: 'from-purple-500 to-pink-500',
  },
]

const stats = [
  { icon: Briefcase, value: '10,000+', label: '职位数据' },
  { icon: TrendingUp, value: '95%', label: '匹配准确率' },
  { icon: Target, value: '7维度', label: '智能分析' },
]

export default function Home() {
  useEffect(() => {
    document.body.classList.add('animated-gradient-bg')
    return () => {
      document.body.classList.remove('animated-gradient-bg')
    }
  }, [])

  return (
    <div className="animate-fade-in">
      {/* Hero Section */}
      <section className="text-center py-16 lg:py-24">
        <div className="flex justify-center mb-6">
          <div className="relative">
            <Logo size={80} />
            <div className="absolute -inset-4 bg-primary-500/20 rounded-full blur-2xl -z-10"></div>
          </div>
        </div>
        
        <h1 className="text-4xl lg:text-6xl font-bold mb-6">
          <span className="gradient-text">DeepCareer</span>
        </h1>
        
        <p className="text-xl lg:text-2xl text-gray-600 mb-4 max-w-2xl mx-auto">
          智能职位匹配系统
        </p>
        
        <p className="text-gray-500 mb-10 max-w-xl mx-auto">
          基于AI的7维度匹配算法，帮助你找到最适合的工作机会
        </p>
        
        <div className="flex flex-wrap justify-center gap-4">
          <Link to="/crawler" className="btn-primary flex items-center gap-2">
            开始使用
            <ArrowRight size={18} />
          </Link>
          <Link to="/jobs" className="btn-secondary">
            浏览职位库
          </Link>
        </div>
      </section>

      {/* Stats */}
      <section className="py-12">
        <div className="grid grid-cols-3 gap-6">
          {stats.map(({ icon: Icon, value, label }) => (
            <div key={label} className="card p-6 text-center">
              <Icon className="w-8 h-8 mx-auto mb-3 text-primary-500" />
              <div className="text-2xl lg:text-3xl font-bold text-gray-900">{value}</div>
              <div className="text-sm text-gray-500">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="py-12">
        <h2 className="text-2xl font-bold text-center mb-10">核心功能</h2>
        
        <div className="grid md:grid-cols-3 gap-6">
          {features.map(({ icon: Icon, title, desc, to, color }) => (
            <Link
              key={title}
              to={to}
              className="card p-6 group hover:scale-[1.02] transition-transform"
            >
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${color} 
                              flex items-center justify-center mb-4 
                              group-hover:scale-110 transition-transform`}>
                <Icon className="w-6 h-6 text-white" />
              </div>
              
              <h3 className="text-lg font-semibold mb-2 group-hover:text-primary-600 transition-colors">
                {title}
              </h3>
              
              <p className="text-gray-500 text-sm">{desc}</p>
              
              <div className="mt-4 flex items-center text-primary-600 text-sm font-medium 
                            opacity-0 group-hover:opacity-100 transition-opacity">
                了解更多 <ArrowRight size={16} className="ml-1" />
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="py-16">
        <div className="card p-8 lg:p-12 text-center bg-gradient-to-br from-primary-500 to-accent-600 text-white">
          <h2 className="text-2xl lg:text-3xl font-bold mb-4">
            准备好开启你的职业新篇章了吗？
          </h2>
          <p className="text-white/80 mb-8 max-w-lg mx-auto">
            上传你的简历，让AI帮你找到最匹配的工作机会
          </p>
          <Link 
            to="/resume" 
            className="inline-flex items-center gap-2 px-6 py-3 bg-white text-primary-600 
                       rounded-lg font-semibold hover:bg-gray-100 transition-colors"
          >
            上传简历
            <ArrowRight size={18} />
          </Link>
        </div>
      </section>
    </div>
  )
}
