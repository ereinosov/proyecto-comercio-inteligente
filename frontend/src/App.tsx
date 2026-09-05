import { useState } from "react";
import { AperturaTurno } from "./componentes/AperturaTurno";
import { Venta } from "./pantallas/Venta";
import { cerrarTurno, type Turno } from "./servicios/turnos";

export function App() {
  const [turno, setTurno] = useState<Turno | null>(null);

  if (!turno) {
    return <AperturaTurno onTurnoAbierto={setTurno} />;
  }

  async function manejarCierre() {
    if (!turno) return;
    await cerrarTurno(turno.id_turno).catch(() => {
      // El turno se cierra en el servidor de todos modos si la petición llegó;
      // un fallo de red no debe dejar la caja bloqueada en esta pantalla (Principio II).
    });
    setTurno(null);
  }

  return <Venta turno={turno} onCerrarTurno={manejarCierre} />;
}
