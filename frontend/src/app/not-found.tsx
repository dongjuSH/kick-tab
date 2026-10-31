import { ButtonLink } from "@/components/ui/Button";
import { StateMessage } from "@/components/ui/DataState";

export default function NotFound() {
  return (
    <div className="kt-container flex flex-1 items-center justify-center py-16">
      <StateMessage
        title="페이지를 찾을 수 없습니다"
        description="주소가 바뀌었거나 아직 준비 중인 페이지입니다."
        action={
          <ButtonLink href="/" variant="secondary">
            경기 일정으로 이동
          </ButtonLink>
        }
      />
    </div>
  );
}
