/**
 * Input rules shown and checked on the screen; the server checks exactly the same (P-04,
 * backend `auth_security.py`).
 */

export const NICKNAME_HINT = "2~12자 · 완성형 한글·영문·숫자 · 중복 불가";
export const PASSWORD_HINT = "8~64자 · 영문·숫자 각각 1자 이상 포함";

export function nicknameValid(value: string): boolean {
  return /^[가-힣A-Za-z0-9]{2,12}$/.test(value);
}

export function passwordValid(value: string): boolean {
  return value.length >= 8 && value.length <= 64 && /[A-Za-z]/.test(value) && /[0-9]/.test(value);
}

export function emailValid(value: string): boolean {
  const email = value.trim();
  return email.length <= 254 && /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email);
}

export interface Confirmations {
  termsOfService: boolean;
  privacyCollection: boolean;
  age14OrOlder: boolean;
}

/**
 * The line under '가입하기' (Figma 637:7298 states): what still blocks signup, or the
 * ready message. Returns `ready: true` only when every condition holds.
 */
export function signupStatus(input: {
  verified: boolean;
  nickname: string;
  password: string;
  passwordConfirm: string;
  confirmations: Confirmations;
}): { ready: boolean; message: string } {
  const { verified, nickname, password, passwordConfirm, confirmations } = input;
  const inputOk = nicknameValid(nickname) && passwordValid(password) && password === passwordConfirm;
  const anyChecked = Object.values(confirmations).some(Boolean);
  if (!verified && !anyChecked) {
    return { ready: false, message: "이메일 인증·입력 조건·필수 확인을 모두 완료해야 가입할 수 있습니다." };
  }
  if (!verified) return { ready: false, message: "이메일 인증을 완료해 주세요." };
  if (!inputOk) return { ready: false, message: "닉네임과 비밀번호 입력을 확인해 주세요." };
  if (!confirmations.termsOfService) return { ready: false, message: "서비스 이용약관 동의를 확인해 주세요." };
  if (!confirmations.privacyCollection) return { ready: false, message: "개인정보 수집·이용 동의를 확인해 주세요." };
  if (!confirmations.age14OrOlder) return { ready: false, message: "만 14세 이상인지 확인해 주세요." };
  return { ready: true, message: "가입하면 바로 로그인됩니다." };
}

/** Field-level hints after the member typed something (empty fields stay quiet). */
export function passwordFieldErrors(password: string, confirm: string) {
  return {
    password: password && !passwordValid(password) ? "비밀번호는 8~64자, 영문과 숫자를 각각 1자 이상 포함해 주세요." : null,
    confirm: confirm && password !== confirm ? "비밀번호 확인이 일치하지 않습니다." : null,
  };
}
