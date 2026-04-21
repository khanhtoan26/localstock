import {getRequestConfig} from 'next-intl/server';
import {locales, defaultLocale} from './routing';
import {cookies, headers} from 'next/headers';

export default getRequestConfig(async () => {
  // 1. Check NEXT_LOCALE cookie
  const cookieStore = await cookies();
  const cookieLocale = cookieStore.get('NEXT_LOCALE')?.value;
  if (cookieLocale && locales.includes(cookieLocale as (typeof locales)[number])) {
    return {
      locale: cookieLocale,
      messages: (await import(`../../messages/${cookieLocale}.json`)).default
    };
  }

  // 2. Detect from Accept-Language header
  const headerStore = await headers();
  const acceptLang = headerStore.get('accept-language') || '';
  const browserLocale = acceptLang.startsWith('vi') ? 'vi' : defaultLocale;

  return {
    locale: browserLocale,
    messages: (await import(`../../messages/${browserLocale}.json`)).default
  };
});
