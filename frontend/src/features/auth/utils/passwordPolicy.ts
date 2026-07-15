export const PASSWORD_POLICY_HINT =
  'Минимум 8 символов, включая цифру, заглавную, строчную буквы и спецсимвол'

export function isPasswordCompliant(password: string): boolean {
  return (
    password.length >= 8 &&
    /\d/.test(password) &&
    /[A-ZА-ЯЁ]/.test(password) &&
    /[a-zа-яё]/.test(password) &&
    /[^A-Za-zА-Яа-яЁё0-9\s]/.test(password)
  )
}
