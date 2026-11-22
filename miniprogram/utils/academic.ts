import type { AffiliationOption } from '../types/api'

export interface AcademicClass {
  id: number
  path: string
  year: number | null
  school: AffiliationOption
  college: AffiliationOption
  department: AffiliationOption
  major: AffiliationOption | null
  label: string
}

export type AcademicFilter = 'school_id' | 'college_id' | 'department_id' | 'major_id' | 'entry_year' | 'class_id'
export type AcademicSelection = Partial<Record<AcademicFilter, number>>

export function academicClasses(nodes: AffiliationOption[]): AcademicClass[] {
  const byId = new Map(nodes.map(node => [node.id, node]))
  const parent = (node?: AffiliationOption) => byId.get(node?.parent_id ?? 0)
  return nodes.flatMap(node => {
    if (node.type !== 'class') return []
    const direct = parent(node)
    const major = direct?.type === 'major' ? direct : null
    const department = major ? parent(major) : direct
    const college = parent(department)
    const school = parent(college)
    if (department?.type !== 'department' || college?.type !== 'college' || school?.type !== 'school') return []
    const year = node.entry_year ?? null
    const label = year && !node.name.includes(`${year}级`) && !node.name.includes(`${year}級`)
      ? `${year}级 ${node.name}` : node.name
    const path = [school.name, college.name, department.name, major?.name, label].filter(Boolean).join(' · ')
    return [{ id: node.id, path, year, school, college, department, major, label }]
  })
}

export function classFilterValue(row: AcademicClass, field: AcademicFilter): number | undefined {
  switch (field) {
    case 'school_id': return row.school.id
    case 'college_id': return row.college.id
    case 'department_id': return row.department.id
    case 'major_id': return row.major?.id
    case 'entry_year': return row.year ?? undefined
    case 'class_id': return row.id
  }
}

export function matchesAcademicSelection(row: AcademicClass, selection: AcademicSelection) {
  return Object.entries(selection).every(([key, id]) => classFilterValue(row, key as AcademicFilter) === id)
}

export function normalizeAcademicKeyword(value: string) {
  return value.toLowerCase().replace(/(\d)\s+(?=[班级級])/g, '$1').replace(/(\d)級/g, '$1级').trim()
}

export function matchesClassKeyword(row: AcademicClass, terms: string[]) {
  const path = normalizeAcademicKeyword(row.path)
  return terms.every(term => /^\d+(班|级)$/.test(term)
    ? new RegExp(`(^|[^0-9])${term}`).test(path)
    : path.includes(term))
}
