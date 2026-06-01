'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';

type Direction = 'ltr' | 'rtl';

interface RTLContextType {
  dir: Direction;
  toggleDir: () => void;
  setDir: (dir: Direction) => void;
}

const RTLContext = createContext<RTLContextType | undefined>(undefined);

export function RTLProvider({ children }: { children: React.ReactNode }) {
  const [dir, setDirState] = useState<Direction>('ltr');

  useEffect(() => {
    const savedDir = localStorage.getItem('dir') as Direction;
    if (savedDir) {
      setDirState(savedDir);
      document.documentElement.dir = savedDir;
      if (savedDir === 'rtl') {
        document.documentElement.classList.add('rtl');
      } else {
        document.documentElement.classList.remove('rtl');
      }
    } else {
      // Default to LTR, but could check browser language
      document.documentElement.dir = 'ltr';
    }
  }, []);

  const setDir = (newDir: Direction) => {
    setDirState(newDir);
    localStorage.setItem('dir', newDir);
    document.documentElement.dir = newDir;
    if (newDir === 'rtl') {
      document.documentElement.classList.add('rtl');
    } else {
      document.documentElement.classList.remove('rtl');
    }
  };

  const toggleDir = () => {
    setDir(dir === 'ltr' ? 'rtl' : 'ltr');
  };

  return (
    <RTLContext.Provider value={{ dir, toggleDir, setDir }}>
      {children}
    </RTLContext.Provider>
  );
}

export function useRTL() {
  const context = useContext(RTLContext);
  if (context === undefined) {
    throw new Error('useRTL must be used within a RTLProvider');
  }
  return context;
}
