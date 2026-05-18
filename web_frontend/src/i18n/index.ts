import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from '../locales/en.json';
import zh from '../locales/zh.json';

const resources = {
  en: { translation: en },
  zh: { translation: zh },
};

// Get saved language from localStorage or use browser default
const getSavedLanguage = () => {
  const saved = localStorage.getItem('i18nextLng');
  if (saved) return saved;
  // Default to browser language if it's Chinese
  const browserLang = navigator.language.toLowerCase();
  return browserLang.startsWith('zh') ? 'zh' : 'en';
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: getSavedLanguage(),
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;
