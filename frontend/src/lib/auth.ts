import type { NextAuthOptions, Session } from "next-auth";
import type { JWT } from "next-auth/jwt";
import GitHubProvider from "next-auth/providers/github";
import CredentialsProvider from "next-auth/providers/credentials";

export const authOptions: NextAuthOptions = {
  providers: [
    GitHubProvider({
      clientId: process.env.GITHUB_ID || "mock_github_id",
      clientSecret: process.env.GITHUB_SECRET || "mock_github_secret",
    }),
    CredentialsProvider({
      id: "credentials",
      name: "Demo Account",
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        // Authenticate as a demo user instantly
        return {
          id: "demo-user",
          name: "Demo User",
          email: "demo@kontracts.pro",
          image: "https://avatars.githubusercontent.com/u/10137?v=4"
        };
      }
    }),
  ],
  pages: {
    signIn: "/login",
  },
  session: {
    strategy: "jwt",
  },
  callbacks: {
    async jwt({ token, account }) {
      if (account?.access_token) {
        token.accessToken = account.access_token;
      }
      return token;
    },
    async session({ session, token }: { session: Session; token: JWT }) {
      return {
        ...session,
        accessToken: token.accessToken,
        user: session.user ? { ...session.user, id: token.sub } : session.user,
      };
    },
  },
};
