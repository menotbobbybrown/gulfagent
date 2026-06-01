"use client";

import { useState, useEffect, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";

interface Skill {
  id: string;
  name: string;
  slug: string;
  description: string;
  category: string;
  icon: string;
  credit_cost: number;
  default_cron: string | null;
}

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [mySkillsSlugs, setMySkillsSlugs] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  const getToken = useCallback(async () => {
    const { data: { session } } = await createClient().auth.getSession();
    return session?.access_token ?? null;
  }, []);

  const fetchData = useCallback(async () => {
    try {
      const token = await getToken();
      if (!token) return;

      const [skillsRes, mineRes] = await Promise.all([
        fetch("/api/skills", { headers: { Authorization: `Bearer ${token}` } }),
        fetch("/api/skills/mine", { headers: { Authorization: `Bearer ${token}` } }),
      ]);

      if (skillsRes.ok) {
        const { data } = await skillsRes.json();
        setSkills(data);
      }
      if (mineRes.ok) {
        const { data } = await mineRes.json();
        setMySkillsSlugs(data.map((s: Skill) => s.slug));
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSeed = async () => {
    try {
      const token = await getToken();
      if (!token) return;
      await fetch("/api/skills/seed", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const toggleSkill = async (slug: string, isActivated: boolean) => {
    try {
      const token = await getToken();
      if (!token) return;
      const method = isActivated ? "DELETE" : "POST";
      const url = `/api/skills/${slug}/${isActivated ? 'deactivate' : 'activate'}`;
      
      const res = await fetch(url, {
        method,
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const categories = Array.from(new Set(skills.map(s => s.category)));
  const mySkills = skills.filter(s => mySkillsSlugs.includes(s.slug));

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="font-display text-2xl font-semibold text-[#E5E0D8]">Skills Marketplace</h1>
          <p className="text-sm text-[#666]">Pre-built AI workflows for GCC businesses.</p>
        </div>
        {skills.length === 0 && !isLoading && (
          <button
            onClick={handleSeed}
            className="px-4 py-2 bg-[#D4A84B]/10 text-[#D4A84B] border border-[#D4A84B]/20 text-sm font-medium rounded-lg hover:bg-[#D4A84B]/20 transition-colors"
          >
            Seed Marketplace
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-[#D4A84B]/20 border-t-[#D4A84B] rounded-full animate-spin" />
        </div>
      ) : (
        <div className="space-y-12">
          {/* Your Skills Section */}
          {mySkills.length > 0 && (
            <section>
              <h2 className="text-xs font-bold text-[#D4A84B] uppercase tracking-widest mb-6 border-b border-[#D4A84B]/10 pb-2">
                Your Active Skills
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {mySkills.map(skill => (
                  <SkillCard
                    key={skill.id}
                    skill={skill}
                    isActivated={true}
                    onToggle={() => toggleSkill(skill.slug, true)}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Marketplace Categories */}
          {categories.map(category => (
            <section key={category}>
              <h2 className="text-xs font-bold text-[#444] uppercase tracking-widest mb-6 border-b border-[#181818] pb-2">
                {category}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {skills
                  .filter(s => s.category === category)
                  .map(skill => {
                    const isActivated = mySkillsSlugs.includes(skill.slug);
                    return (
                      <SkillCard
                        key={skill.id}
                        skill={skill}
                        isActivated={isActivated}
                        onToggle={() => toggleSkill(skill.slug, isActivated)}
                      />
                    );
                  })
                }
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

function SkillCard({ skill, isActivated, onToggle }: { skill: Skill, isActivated: boolean, onToggle: () => void }) {
  return (
    <div className="bg-[#0D0D0D] border border-[#181818] rounded-2xl p-6 flex flex-col h-full hover:border-[#D4A84B]/30 transition-all group">
      <div className="flex items-start justify-between mb-4">
        <div className="w-10 h-10 rounded-xl bg-[#141414] border border-[#181818] flex items-center justify-center text-xl group-hover:scale-110 transition-transform">
          {getEmoji(skill.icon)}
        </div>
        <div className="text-right">
          <span className="block text-[10px] text-[#444] font-bold uppercase tracking-tight">Cost</span>
          <span className="text-[#D4A84B] text-sm font-semibold">{skill.credit_cost} <span className="text-[10px] opacity-60">credits</span></span>
        </div>
      </div>
      <h3 className="text-[#E5E0D8] font-semibold mb-2">{skill.name}</h3>
      <p className="text-sm text-[#666] flex-1 mb-6 leading-relaxed">
        {skill.description}
      </p>
      <button
        onClick={onToggle}
        className={`w-full py-2.5 rounded-xl text-sm font-medium transition-all ${
          isActivated
            ? "bg-[#181818] text-[#888] hover:text-red-400 border border-transparent hover:border-red-900/30"
            : "bg-[#D4A84B] text-black hover:bg-[#C59B3F]"
        }`}
      >
        {isActivated ? "Deactivate" : "Activate"}
      </button>
    </div>
  );
}

function getEmoji(icon: string) {
  const emojis: Record<string, string> = {
    newspaper: "📰",
    "trending-down": "📉",
    search: "🔍",
    mail: "📧",
    eye: "👁️",
    bell: "🔔",
    users: "👥",
    "bar-chart": "📊",
    "file-text": "📄",
    "message-square": "💬",
  };
  return emojis[icon] || "🤖";
}
