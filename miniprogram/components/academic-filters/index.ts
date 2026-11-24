import { AcademicClass, AcademicFilter, AcademicSelection, classFilterValue, matchesAcademicSelection } from '../../utils/academic'

const fields: Array<{ key: AcademicFilter; label: string }> = [
  { key: 'school_id', label: '学校' },
  { key: 'college_id', label: '学院' },
  { key: 'department_id', label: '系别' },
  { key: 'major_id', label: '专业' },
  { key: 'entry_year', label: '入学年份' },
  { key: 'class_id', label: '班级' },
]

function labelFor(row: AcademicClass, key: AcademicFilter) {
  switch (key) {
    case 'school_id': return row.school.name
    case 'college_id': return `${row.school.name} · ${row.college.name}`
    case 'department_id': return `${row.college.name} · ${row.department.name}`
    case 'major_id': return row.major ? `${row.department.name} · ${row.major.name}` : undefined
    case 'entry_year': return row.year ? `${row.year}级` : undefined
    case 'class_id': return row.path
  }
}

type Filter = typeof fields[number] & { choices: Array<{ id: number; name: string }>; current: string }
interface FilterComponent {
  data: { classes: AcademicClass[]; showSchool: boolean; filters: Filter[]; selection: AcademicSelection }
  setData(data: Partial<FilterComponent['data']>): void
  triggerEvent(name: string, selection: AcademicSelection): void
  rebuild(): void
}

Component({
  properties: {
    classes: { type: Array, value: [] },
    showSchool: { type: Boolean, value: false },
    compact: { type: Boolean, value: false },
    tiles: { type: Boolean, value: false },
  },
  data: { filters: [] as Filter[], selection: {} as AcademicSelection },
  observers: {
    'classes, showSchool'(this: FilterComponent) { this.rebuild() },
  },
  methods: {
    rebuild(this: FilterComponent) {
      const filters: Filter[] = []
      const preceding: AcademicSelection = {}
      const classes = this.data.classes
      for (const field of fields) {
        if (field.key === 'school_id' && !this.data.showSchool) continue
        const options = new Map<number, string>()
        for (const row of classes) {
          if (!matchesAcademicSelection(row, preceding)) continue
          const id = classFilterValue(row, field.key)
          const label = labelFor(row, field.key)
          if (id !== undefined && label) options.set(id, label)
        }
        const selected = this.data.selection[field.key]
        const current = selected ? options.get(selected) : undefined
        const choices = [{ id: 0, name: `全部${field.label}` },
          ...Array.from(options, ([id, name]) => ({ id, name }))]
        if (choices.length > 1) filters.push({ ...field, choices, current: current || field.label })
        if (current && selected) preceding[field.key] = selected
      }
      this.setData({ filters })
    },
    select(this: FilterComponent, e: WechatMiniprogram.PickerChange) {
      const key = e.currentTarget.dataset.key as AcademicFilter
      const filter = this.data.filters.find(row => row.key === key)
      const selected = filter?.choices[Number(e.detail.value)]
      if (!selected) return
      const selection: AcademicSelection = {}
      for (const field of fields) {
        if (field.key === key) break
        const id = this.data.selection[field.key]
        if (id) selection[field.key] = id
      }
      if (selected.id) selection[key] = selected.id
      this.setData({ selection })
      this.rebuild()
      this.triggerEvent('select', selection)
    },
  },
})
