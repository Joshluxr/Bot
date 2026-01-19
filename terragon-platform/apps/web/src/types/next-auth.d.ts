import 'next-auth';

declare module 'next-auth' {
  interface Session {
    user: {
      id: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
      githubToken?: string;
    };
    accessToken?: string;
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    id: string;
    githubToken?: string;
    accessToken?: string;
  }
}
