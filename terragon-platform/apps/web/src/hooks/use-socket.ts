'use client';

import { useEffect, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { useSession } from 'next-auth/react';
import type { WebSocketEvent } from '@terragon/shared';

const SOCKET_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';

let socket: Socket | null = null;

export function useSocket() {
  const { data: session } = useSession();
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!session?.user) {
      return;
    }

    // Create socket connection if not exists
    if (!socket) {
      socket = io(SOCKET_URL, {
        auth: {
          token: (session as any).accessToken,
        },
        transports: ['websocket'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
      });
    }

    socket.on('connect', () => {
      console.log('Socket connected');
      setIsConnected(true);
    });

    socket.on('disconnect', () => {
      console.log('Socket disconnected');
      setIsConnected(false);
    });

    socket.on('connect_error', (error) => {
      console.error('Socket connection error:', error);
    });

    return () => {
      // Don't disconnect on unmount, keep connection alive
    };
  }, [session]);

  const subscribeToTask = useCallback((taskId: string) => {
    if (socket?.connected) {
      socket.emit('subscribe:task', taskId);
    }
  }, []);

  const unsubscribeFromTask = useCallback((taskId: string) => {
    if (socket?.connected) {
      socket.emit('unsubscribe:task', taskId);
    }
  }, []);

  const onEvent = useCallback(
    (event: string, callback: (data: any) => void) => {
      if (socket) {
        socket.on(event, callback);
        return () => {
          socket?.off(event, callback);
        };
      }
      return () => {};
    },
    []
  );

  return {
    isConnected,
    subscribeToTask,
    unsubscribeFromTask,
    onEvent,
    socket,
  };
}

export function useTaskEvents(
  taskId: string,
  handlers: {
    onStarted?: (data: any) => void;
    onProgress?: (data: any) => void;
    onCompleted?: (data: any) => void;
    onFailed?: (data: any) => void;
    onLog?: (data: any) => void;
  }
) {
  const { subscribeToTask, unsubscribeFromTask, onEvent } = useSocket();

  useEffect(() => {
    subscribeToTask(taskId);

    const cleanups: (() => void)[] = [];

    if (handlers.onStarted) {
      cleanups.push(onEvent('task:started', handlers.onStarted));
    }
    if (handlers.onProgress) {
      cleanups.push(onEvent('task:progress', handlers.onProgress));
    }
    if (handlers.onCompleted) {
      cleanups.push(onEvent('task:completed', handlers.onCompleted));
    }
    if (handlers.onFailed) {
      cleanups.push(onEvent('task:failed', handlers.onFailed));
    }
    if (handlers.onLog) {
      cleanups.push(onEvent('log', handlers.onLog));
    }

    return () => {
      unsubscribeFromTask(taskId);
      cleanups.forEach((cleanup) => cleanup());
    };
  }, [taskId, subscribeToTask, unsubscribeFromTask, onEvent]);
}
