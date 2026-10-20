<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <div style="font-size: 16px; font-weight: bold">
            <span>{{ lab?.name || '实验室' }}设备列表</span>
          </div>
          <div>
            <el-button type="primary" @click="hanldeReserveLab">预约实验室</el-button>
            <el-button @click="router.push('/manager/lablist')">返回实验室列表</el-button>
          </div>
        </div>
      </template>
      <div
        v-if="lab"
        style="color: #666; margin-bottom: 16px; background-color: antiquewhite; padding: 10px"
      >
        <div style="margin-bottom: 10px">简介：{{ lab.description }}</div>
        <div>
          位置：{{ lab.location }}
          <span style="margin: 0 10px">|</span>
          容纳 {{ lab.capacity }} 人
          <span style="margin: 0 10px">|</span>
          开放：{{ lab.open_time && lab.close_time ? `${lab.open_time} - ${lab.close_time}` : '-' }}
        </div>
      </div>
      <el-table
        :header-cell-style="{ backgroundColor: '#fdf', color: '#333' }"
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column prop="img" label="图片" width="90">
          <template #default="{ row }">
            <div style="min-height: 50px">
              <el-image
                v-if="row.img"
                style="display: block; width: 50px; height: 50px; border-radius: 6px"
                :src="row.img"
                :preview-src-list="[row.img]"
                :preview-teleported="true"
                alt=""
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="设备名称" />
        <el-table-column prop="spec" label="型号规格" />
        <el-table-column prop="quantity" label="数量" width="80" />
        <el-table-column prop="lab_name" label="所属实验室" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? '正常' : '维修' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button
              :disabled="!row.status"
              type="primary"
              text
              bg
              @click="hanldeReserveEquipment(row)"
              >预约</el-button
            >
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 10px; display: flex; justify-content: flex-end">
        <el-pagination
          v-model:current-page="params.page"
          v-model:page-size="params.page_size"
          :total="total"
          background
          layout="total, prev, pager, next"
          @current-change="loadEquipment"
        />
      </div>
    </el-card>
    <reserve-dialog
      v-model:visible="reserveVisible"
      :lab-id="lab?.id"
      :lab-name="lab?.name"
      :equipment-id="currentEquipment?.id"
      :equipment-name="currentEquipment?.name"
    ></reserve-dialog>
  </div>
</template>

<script setup>
import { getLab } from '@/api/lab'
import { ElMessage } from 'element-plus'
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getEquipmentPageList } from '@/api/equipment'
import ReserveDialog from '@/components/ReserveDialog.vue'
const route = useRoute()
const router = useRouter()
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const lab = ref(null)
const reserveVisible = ref(false)
const currentEquipment = ref(null)
const params = reactive({
  page: 1,
  page_size: 10,
  lab_id: Number(route.query.lab_id) // "8" -> 8
})

// 加载设备分页数据
const loadEquipment = async () => {
  loading.value = true
  try {
    const res = await getEquipmentPageList(params)
    if (res.code === 200) {
      tableData.value = res.data?.list ?? []
      total.value = res.data?.total ?? 0
    }
  } catch {
    // 请求失败时由请求拦截器提示错误。
  } finally {
    loading.value = false
  }
}

const hanldeReserveLab = () => {
  currentEquipment.value = null
  reserveVisible.value = true
}
const hanldeReserveEquipment = (equipment) => {
  currentEquipment.value = equipment
  reserveVisible.value = true
}
const loadLab = async () => {
  try {
    const res = await getLab(params.lab_id)
    if (res.code === 200) {
      lab.value = res.data
    }
  } catch {
    // 请求失败时由请求拦截器提示错误。
  }
}

onMounted(() => {
  if (!Number.isInteger(params.lab_id) || params.lab_id <= 0) {
    ElMessage.warning('缺少有效的实验室查询条件 [lab_id]')
    return
  }
  loadLab()
  loadEquipment()
})
</script>
