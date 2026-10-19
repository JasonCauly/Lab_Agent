<template>
  <div style="width: 50%">
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>设备管理</span>
        </div>
      </template>
      <div style="margin-bottom: 10px">
        <el-select
          v-model="params.lab_id"
          placeholder="所属实验室"
          clearable
          style="width: 200px; margin-right: 8px"
          @change="handleSearch"
        >
          <el-option
            v-for="item in labOptions"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </el-select>

        <el-input
          placeholder="请输入设备名称或型号"
          v-model="params.keywords"
          style="width: 240px; margin-right: 8px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        ></el-input>

        <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
        <el-button type="success" :icon="Plus" @click="handleCreate">新增</el-button>
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
              <img
                v-if="row.img"
                style="display: block; width: 50px; height: 50px; border-radius: 6px"
                :src="row.img"
                alt=""
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="lab_name" label="所属实验室" />
        <el-table-column prop="name" label="设备名称" />

        <el-table-column prop="spec" label="型号规格" />
        <el-table-column prop="quantity" label="数量" width="80" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? '正常' : '维修' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="primary" text bg @click="handleEdit(row)">编辑</el-button>
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
          @current-change="load"
        />
      </div>
      <el-dialog v-model="dialogVisible" :title="form.id ? '编辑' : '新增'" width="450">
        <el-form
          id="user-form"
          ref="formRef"
          :rules="rules"
          :model="form"
          label-width="80px"
          style="width: 100%; padding-right: 30px; padding-top: 16px"
          v-loading="formLoading"
          @submit.prevent="handleSave"
        >
          <el-form-item label="所属实验室" prop="lab_id">
            <el-select v-model="form.lab_id" placeholder="请选择实验室" style="width: 100%">
              <el-option
                v-for="item in labOptions"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="设备名称" prop="name">
            <el-input v-model="form.name" placeholder="请输入设备名称" />
          </el-form-item>

          <el-form-item label="说明">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="3"
              placeholder="请输入说明"
            />
          </el-form-item>

          <el-form-item label="图片">
            <el-upload
              class="avatar-uploader"
              :http-request="handleFileUpload"
              :show-file-list="false"
              accept="image/jpeg,image/png,image/gif,image/webp"
              :before-upload="beforeAvatarUpload"
            >
              <img v-if="form.img" :src="form.img" class="avatar" />
              <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>
            </el-upload>
          </el-form-item>

          <el-form-item label="型号规格">
            <el-input v-model="form.spec" placeholder="例如 RTX4090 24G" />
          </el-form-item>

          <el-form-item label="数量" prop="quantity">
            <el-input-number v-model="form.quantity" :min="1" :max="999" />
          </el-form-item>

          <el-form-item label="状态">
            <el-radio-group v-model="form.status">
              <el-radio :value="1">正常</el-radio>
              <el-radio :value="0">维修</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button type="primary" native-type="submit" form="user-form" :loading="formLoading">
            确定
          </el-button>
          <el-button :disabled="formLoading" @click="dialogVisible = false">取消</el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import {
  getEquipmentPageList,
  createEquipmentApi,
  updateEquipmentApi,
  deleteEquipmentApi
} from '@/api/equipment'
import { getLabPageList } from '@/api/lab'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { uploadFileApi } from '@/api/files'

const params = reactive({
  page: 1,
  page_size: 10,
  keywords: '',
  lab_id: null
})

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const labOptions = ref([])
const dialogVisible = ref(false)
const formRef = ref()
const formLoading = ref(false)
const form = reactive({
  id: null,
  lab_id: null,
  name: '',
  description: '',
  img: '',
  spec: '',
  quantity: 1,
  status: 1
})

// 加载分页数据
const load = async () => {
  loading.value = true
  try {
    const res = await getEquipmentPageList(params)
    if (res.code === 200) {
      tableData.value = res.data?.list
      total.value = res.data?.total
    }
  } finally {
    loading.value = false
  }
}

const rules = {
  lab_id: [{ required: true, message: '请选择实验室', trigger: 'change' }],
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  quantity: [{ required: true, message: '请输入数量', trigger: 'blur' }]
}

const resetForm = () => {
  Object.assign(form, {
    id: null,
    name: '',
    description: '',
    img: '',
    location: '',
    capacity: 20,
    open_time: '08:30',
    close_time: '20:30',
    status: true
  })
}

const handleSearch = () => {
  params.page = 1
  load()
}

const handleCreate = async () => {
  resetForm()
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

// 编辑信息
const handleEdit = (row) => {
  resetForm()
  Object.assign(form, {
    id: row.id,
    lab_id: row.lab_id,
    name: row.name,
    description: row.description,
    img: row.img,
    spec: row.spec,
    quantity: row.quantity,
    status: row.status
  })
  dialogVisible.value = true
}

// 删除信息
const handleDelete = (row) => {
  ElMessageBox.confirm(`确认删除【${row.name}】？`, '确认删除', { type: 'warning' }).then(
    async () => {
      const res = await deleteEquipmentApi(row.id)
      if (res.code === 200) {
        ElMessage.success('删除成功')
        load()
      }
    }
  )
}

// 保存信息
const handleSave = async () => {
  if (formLoading.value || !formRef.value) return
  formLoading.value = true
  try {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
    const { id, ...equipmentData } = form
    const res = id
      ? await updateEquipmentApi(id, equipmentData)
      : await createEquipmentApi(equipmentData)
    if (res.code === 200) {
      dialogVisible.value = false
      ElMessage.success('操作成功')
      await load()
    }
  } catch {
    // 请求失败时由请求拦截器提示错误，保留表单以便重试。
  } finally {
    formLoading.value = false
  }
}

const beforeAvatarUpload = (file) => {
  const imageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']

  if (!imageTypes.includes(file.type)) {
    ElMessage.error('只能上传图片')
    return false
  }

  if (file.size / 1024 / 1024 > 2) {
    ElMessage.error('上传图片大小不能超过2M')
    return false
  }

  return true
}

const handleFileUpload = async ({ file }) => {
  try {
    const res = await uploadFileApi(file)
    if (res.code === 200) {
      form.img = res.data?.url
    }
  } catch {}
}

const loadLabs = async () => {
  const res = await getLabPageList({ page: 1, page_size: 100 })
  if (res.code === 200) {
    labOptions.value = res.data?.list
  }
}

onMounted(() => {
  loadLabs()
  load()
})
</script>

<style scoped>
.avatar-uploader .avatar {
  width: 130px;
  height: 130px;
  display: block;
}
</style>
<style>
.avatar-uploader .el-upload {
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: var(--el-transition-duration-fast);
}
.avatar-uploader .el-upload:hover {
  border-color: var(--el-color-primary);
}
.el-icon.avatar-uploader-icon {
  font-size: 28px;
  color: #8c939d;
  width: 130px;
  height: 130px;
  text-align: center;
}
</style>
