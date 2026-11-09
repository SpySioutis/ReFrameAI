"use client";

import { useEffect } from "react";
import { create } from "zustand";

const TOKEN_KEY = "reframe-token";

interface AuthState {
  token: string | null;
  email: string | null;
  setAuth: (token: string, email: string) => void;
  logout: () => void;
  hydrated: boolean;
}

export const useAuth = create<AuthState>((set) => ({
  token: null,
  email: null,
  hydrated: false,
  setAuth: (token, email) => {
    try {
      localStorage.setItem(TOKEN_KEY, JSON.stringify({ token, email }));
    } catch {
      /* ignore */
    }
    set({ token, email, hydrated: true });
  },
  logout: () => {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* ignore */
    }
    set({ token: null, email: null, hydrated: true });
  },
}));

export function useHydrateAuth() {
  useEffect(() => {
    try {
      const raw = localStorage.getItem(TOKEN_KEY);
      if (raw) {
        const { token, email } = JSON.parse(raw);
        useAuth.setState({ token, email, hydrated: true });
        return;
      }
    } catch {
      /* ignore */
    }
    useAuth.setState({ hydrated: true });
  }, []);
}

export interface EditorSelection {
  objectId: string;
  trackingId: number;
  frame: number;
  box: { x1: number; y1: number; x2: number; y2: number };
  provider: string;
}

interface EditorState {
  projectId: string | null;
  currentFrame: number;
  selection: EditorSelection | null;
  setProject: (id: string) => void;
  setFrame: (f: number) => void;
  setSelection: (s: EditorSelection | null) => void;
}

export const useEditor = create<EditorState>((set) => ({
  projectId: null,
  currentFrame: 0,
  selection: null,
  setProject: (projectId) => set({ projectId, selection: null, currentFrame: 0 }),
  setFrame: (currentFrame) => set({ currentFrame }),
  setSelection: (selection) => set({ selection }),
}));
