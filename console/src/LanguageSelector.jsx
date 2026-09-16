import React from 'react';
import {Globe} from 'lucide-react';
import {languages, setLocale, useLocale, t, documentationUrl} from './i18n';
export default function LanguageSelector() {
  const locale = useLocale();
  return <div className="td-language"><label><Globe size={15}/><select aria-label={t('Language')} value={locale} onChange={event=>setLocale(event.target.value)}>{languages.map(([code,label])=><option key={code} value={code}>{label}</option>)}</select></label><a href={documentationUrl()} target="_blank" rel="noreferrer">{t('Documentation')}</a></div>;
}
