import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import PatientListView from '../views/PatientListView.vue'
import PatientDetailView from '../views/PatientDetailView.vue'
import PatientCreateView from '../views/PatientCreateView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/patients',
      name: 'patient-list',
      component: PatientListView
    },
    {
      path: '/patients/create',
      name: 'patient-create',
      component: PatientCreateView
    },
    {
      path: '/patients/:id',
      name: 'patient-detail',
      component: PatientDetailView,
      props: true
    }
  ]
})

export default router
