'use client';

import React from 'react';
import Link from 'next/link';

export default function WelcomePage() {
  return (
    <div className="min-h-screen bg-[#0A0A0A] text-[#E5E0D8] font-sans rtl" dir="rtl">
      <div className="max-w-4xl mx-auto px-6 py-20 text-center">
        <div className="w-20 h-20 rounded-2xl bg-[#D4A84B]/10 border border-[#D4A84B]/20 flex items-center justify-center mx-auto mb-8">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L3 7v10l9 5 9-5V7L12 2z" stroke="#D4A84B" strokeWidth="1.5" strokeLinejoin="round" />
            <path d="M12 2v20M3 7l9 5 9-5" stroke="#D4A84B" strokeWidth="1.5" strokeLinejoin="round" />
          </svg>
        </div>
        
        <h1 className="font-display text-4xl md:text-6xl font-bold mb-6 tracking-tight">
          مرحباً بك في <span className="text-[#D4A84B]">GulfAgent</span>
        </h1>
        
        <p className="text-xl text-[#888] mb-12 max-w-2xl mx-auto leading-relaxed">
          المنصة الأولى في الخليج لأتمتة المهام عبر الذكاء الاصطناعي. 
          نفذ مهامك التجارية، ابحث في المواقع المحلية، وأدر أعمالك عبر الواتساب بسهولة.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4 justify-center mb-20">
          <Link 
            href="/login" 
            className="px-8 py-4 bg-[#D4A84B] text-black font-semibold rounded-xl hover:bg-[#C59B3F] transition-all text-lg"
          >
            ابدأ الآن مجاناً
          </Link>
          <Link 
            href="https://wa.me/your-number" 
            className="px-8 py-4 bg-white/5 border border-white/10 text-white font-semibold rounded-xl hover:bg-white/10 transition-all text-lg"
          >
            جرب عبر الواتساب
          </Link>
        </div>
        
        <div className="grid md:grid-cols-3 gap-8 text-right">
          <div className="p-6 rounded-2xl bg-[#0D0D0D] border border-[#181818]">
            <div className="w-12 h-12 rounded-xl bg-[#D4A84B]/10 flex items-center justify-center mb-4">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#D4A84B" strokeWidth="2">
                <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 1 1-7.6-4.7 8.38 8.38 0 0 1 3.8.9L21 3l-3.9 11.5Z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold mb-2">عميل متصفح ذكي</h3>
            <p className="text-[#666]">يمكن لـ GulfAgent تصفح المواقع، تعبئة النماذج، واستخراج البيانات من المواقع المحلية مثل Noon وTalabat.</p>
          </div>
          
          <div className="p-6 rounded-2xl bg-[#0D0D0D] border border-[#181818]">
            <div className="w-12 h-12 rounded-xl bg-[#D4A84B]/10 flex items-center justify-center mb-4">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#D4A84B" strokeWidth="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold mb-2">واجهة واتساب أصلية</h3>
            <p className="text-[#666]">أرسل مهامك باللغة العربية عبر الواتساب واحصل على النتائج فوراً. سهولة تامة في الاستخدام.</p>
          </div>
          
          <div className="p-6 rounded-2xl bg-[#0D0D0D] border border-[#181818]">
            <div className="w-12 h-12 rounded-xl bg-[#D4A84B]/10 flex items-center justify-center mb-4">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#D4A84B" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            </div>
            <h3 className="text-xl font-bold mb-2">أتمتة ذكية</h3>
            <p className="text-[#666]">قم بجدولة المهام المتكررة، مثل التحقق من المخالفات المرورية أو أسعار المنتجات، واحصل على تنبيهات تلقائية.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
