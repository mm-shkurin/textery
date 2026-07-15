export const PASSWORD_POLICY_HINT =
  'Минимум 8 символов, включая цифру, заглавную, строчную буквы и спецсимвол'

export function isPasswordCompliant(password: string): boolean {
  return (
    password.length >= 8 &&
    /\d/.test(password) &&
    /[A-ZА-Я]/.test(password) &&
    /[a-zа-я]/.test(password) &&
    /[^A-Za-zА-Яа-я0-9]/.test(password)
  )
}
