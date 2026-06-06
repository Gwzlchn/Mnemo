import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
    },
    {
      path: '/jobs',
      name: 'jobs',
      component: () => import('../views/JobListView.vue'),
    },
    {
      path: '/jobs/:id',
      name: 'job-detail',
      component: () => import('../views/JobDetailView.vue'),
    },
    {
      path: '/notes/:jobId',
      name: 'notes',
      component: () => import('../views/NotesView.vue'),
    },
    {
      path: '/notes/:jobId/mechanical',
      name: 'notes-mechanical',
      component: () => import('../views/NotesView.vue'),
    },
    {
      path: '/workers',
      name: 'workers',
      component: () => import('../views/WorkersView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/SettingsView.vue'),
    },
  ],
})

export default router
