import NextAuth from 'next-auth';
import GithubProvider from 'next-auth/providers/github';
import GoogleProvider from 'next-auth/providers/google';
import { PrismaAdapter } from '@auth/prisma-adapter';
import { prisma } from '@terragon/database';
import jwt from 'jsonwebtoken';

const handler = NextAuth({
  adapter: PrismaAdapter(prisma) as any,
  providers: [
    GithubProvider({
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
      authorization: {
        params: {
          scope: 'read:user user:email repo',
        },
      },
    }),
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  session: {
    strategy: 'jwt',
  },
  callbacks: {
    async jwt({ token, user, account }) {
      if (user) {
        token.id = user.id;
        // Generate a JWT token for API authentication
        token.accessToken = jwt.sign(
          { id: user.id, email: user.email },
          process.env.JWT_SECRET || process.env.NEXTAUTH_SECRET!,
          { expiresIn: '7d' }
        );
      }
      if (account?.provider === 'github') {
        token.githubToken = account.access_token;

        // Store the GitHub token in the database
        try {
          await prisma.user.update({
            where: { id: token.id as string },
            data: { githubToken: account.access_token },
          });
        } catch {
          // User might not exist yet during first login
        }
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string;
        session.user.githubToken = token.githubToken as string | undefined;
      }
      session.accessToken = token.accessToken as string | undefined;
      return session;
    },
  },
  pages: {
    signIn: '/login',
  },
});

export { handler as GET, handler as POST };
