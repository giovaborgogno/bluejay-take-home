import Image from 'next/image';
import { Button } from '@/components/livekit/button';

function WelcomeImage() {
  return <Image src="/claro-logo.svg" alt="Claro" width={80} height={80} className="mb-4" />;
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div ref={ref}>
      <section className="bg-background flex flex-col items-center justify-center text-center">
        <WelcomeImage />

        <p className="text-foreground max-w-prose pt-1 leading-6 font-medium">
          Tu asistente de Claro está listo para ayudarte con todo lo que necesites
        </p>

        <Button variant="primary" size="lg" onClick={onStartCall} className="mt-6 w-64 font-mono">
          {startButtonText}
        </Button>
      </section>

      <div className="fixed bottom-5 left-0 flex w-full items-center justify-center">
        <p className="text-muted-foreground max-w-prose pt-1 text-xs leading-5 font-normal text-pretty md:text-sm">
          ¿Necesitas ayuda? Estamos aquí para ti.
        </p>
      </div>
    </div>
  );
};
