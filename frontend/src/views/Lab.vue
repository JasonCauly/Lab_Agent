<template>
  <div style="width: 50%">
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>实验室管理</span>
        </div>
      </template>
      <div style="margin-bottom: 10px">
        <el-input
          placeholder="请输入账号或名称查询"
          v-model="params.keywords"
          style="width: 240px; margin-right: 8px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        ></el-input>
        <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
        <el-button type="primary" :icon="Plus" @click="handleCreate">新增</el-button>
      </div>
      <el-table
        :header-cell-style="{ backgroundColor: '#fdf', color: '#333' }"
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column prop="img" label="封面" width="100">
          <template #default="{ row }">
            <div style="min-height: 50px">
              <img
                v-if="row.img"
                style="display: block; width: 50px; height: 50px; border-radius: 50%"
                :src="row.img"
                alt=""
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" width="140" />
        <el-table-column prop="description" label="简介" width="140" />
        <el-table-column prop="location" label="位置" width="200" />
        <el-table-column label="开放时间">
          <template #default="{ row }">{{ row.open_time }} - {{ row.close_time }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'">
              {{ row.status ? '开启' : '关闭' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="primary" text bg @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" text bg @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 10px; display: flex; justify-content: flex-end">
        <el-pagination
          v-model:current-page="params.page"
          v-model:page-size="params.pageSize"
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
          <el-form-item label="名称" prop="name">
            <el-input v-model="form.name" placeholder="请输入名称" />
          </el-form-item>

          <el-form-item label="简介">
            <el-input type="textarea" v-model="form.description" placeholder="请输入简介" />
          </el-form-item>

          <el-form-item label="封面">
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
          <el-form-item label="位置">
            <el-input type="textarea" v-model="form.location" placeholder="请输入位置" />
          </el-form-item>
          <el-form-item label="容量" prop="capacity">
            <el-input-number v-model="form.capacity" :min="1" :precision="0" placeholder="请输入容量" />
          </el-form-item>
          <el-form-item label="开放时间">
            <el-time-picker
              v-model="form.open_time"
              format="HH:mm"
              value-format="HH:mm"
              placeholder="开始时间"
              style="width: 140px; margin-right: 8px"
            />
            <el-time-picker
              v-model="form.close_time"
              format="HH:mm"
              value-format="HH:mm"
              placeholder="结束时间"
              style="width: 140px"
            />
          </el-form-item>
          <el-form-item label="状态" prop="status" for="">
            <el-radio-group v-model="form.status">
              <el-radio :value="true">正常</el-radio>
              <el-radio :value="false">禁用</el-radio>
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
import { getLabPageList, createLabApi, updateLabApi, deleteLabApi } from '@/api/lab'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { uploadFileApi } from '@/api/files'

const params = reactive({
  page: 1,
  pageSize: 10,
  keywords: ''
})

// 加载分页数据
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const formRef = ref()
const formLoading = ref(false)
const form = reactive({
  id: null,
  name: '',
  description: '',
  img: '',
  location: '',
  capacity: 1,
  open_time: '',
  close_time: '',
  status: true
})

const load = async () => {
  loading.value = true
  try {
    const res = await getLabPageList({
      page: params.page,
      page_size: params.pageSize,
      keywords: params.keywords
    })
    if (res.code === 200) {
      tableData.value = res.data?.list
      total.value = res.data?.total
    }
  } finally {
    loading.value = false
  }
}

const rules = computed(() => ({
  name: [{ required: true, message: '请输入实验室名称', trigger: 'blur' }],
  capacity: [
    { required: true, message: '请输入容量', trigger: 'blur' },
    { type: 'integer', min: 1, message: '容量必须为正整数', trigger: 'change' }
  ]
}))

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

const handleSearch = async () => {
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
const handleEdit = async (row) => {
  resetForm()
  Object.assign(form, {
    id: row.id,
    name: row.name,
    description: row.description,
    img: row.img,
    location: row.location,
    capacity: row.capacity,
    open_time: row.open_time,
    close_time: row.close_time,
    status: row.status
  })
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

// 删除信息
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除【${row.name}】？`, '确认删除', { type: 'warning' })
    const res = await deleteLabApi(row.id)
    if (res.code === 200) {
      ElMessage.success('删除成功')
      await load()
    }
  } catch {
    // 取消或关闭确认框无需处理，请求失败时由请求拦截器提示错误。
  }
}

// 保存信息
const handleSave = async () => {
  if (formLoading.value || !formRef.value) return
  formLoading.value = true
  try {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
    const { id, ...labData } = form
    const res = id ? await updateLabApi(id, labData) : await createLabApi(labData)
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

onMounted(() => {
  load()
})

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
