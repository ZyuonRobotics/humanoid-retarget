import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import enUS from 'antd/locale/en_US'
import zhCN from 'antd/locale/zh_CN'
import App from './App'
import './i18n'
import './index.css'

const getAntdLocale = () => {
  const lang = localStorage.getItem('i18nextLng') || 'en'
  return lang === 'zh' ? zhCN : enUS
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={getAntdLocale()}
      theme={{
        token: {
          colorPrimary: '#1677ff',
        },
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>,
)
