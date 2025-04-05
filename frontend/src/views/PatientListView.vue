<template>
  <div class="patient-list">
    <h1>患者列表</h1>
    <div class="search-bar">
      <input v-model="searchQuery" placeholder="搜索患者...">
    </div>
    <div v-if="isLoading" class="loading">加载中...</div>
    <div v-else-if="error" class="error">
      加载失败: {{ error.message }}
      <button @click="fetchPatients">重试</button>
    </div>
    <template v-else>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>姓名</th>
            <th>性别</th>
            <th>年龄</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="patient in filteredPatients" :key="patient.id">
            <td>{{ patient.id }}</td>
            <td>{{ patient.name }}</td>
            <td>{{ patient.gender }}</td>
            <td>{{ patient.age }}</td>
            <td>
              <button @click="viewDetail(patient.id)">查看</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="filteredPatients.length === 0" class="empty">
        没有找到匹配的患者
      </div>
    </template>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, onMounted } from 'vue'
import type { Patient } from '@/types/patient'
import api from '@/services/api'

export default defineComponent({
  name: 'PatientListView',
  setup() {
    const searchQuery = ref('')
    const patients = ref<Patient[]>([])
    const isLoading = ref(false)
    const error = ref(null)

    const fetchPatients = async () => {
      try {
        isLoading.value = true
        const response = await api.getPatients()
        patients.value = response.data
      } catch (err) {
        error.value = err
        console.error('获取患者列表失败:', err)
      } finally {
        isLoading.value = false
      }
    }

    onMounted(() => {
      fetchPatients()
    })

    const filteredPatients = computed(() => {
      return patients.value.filter(patient => 
        patient.name.includes(searchQuery.value)
      )
    })

    const viewDetail = (id: number) => {
      // 路由跳转到患者详情页
      console.log('查看患者详情:', id)
    }

    return {
      searchQuery,
      patients,
      filteredPatients,
      viewDetail
    }
  }
})
</script>

<style scoped>
.patient-list {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.search-bar {
  margin: 20px 0;
}

.search-bar input {
  padding: 8px 12px;
  width: 300px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

th, td {
  border: 1px solid #ddd;
  padding: 12px;
  text-align: left;
}

th {
  background-color: #f5f5f5;
}

button {
  padding: 6px 12px;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:hover {
  background-color: #40a9ff;
}

.loading,
.error,
.empty {
  padding: 20px;
  text-align: center;
  margin: 20px 0;
  border-radius: 4px;
}

.loading {
  background-color: #f5f5f5;
  color: #666;
}

.error {
  background-color: #fff2f0;
  color: #f5222d;
}

.empty {
  background-color: #f5f5f5;
  color: #666;
}
</style>
