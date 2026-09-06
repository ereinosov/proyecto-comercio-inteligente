/**
 * Pantalla de Cobertura de medios de pago (007-pagos-seguridad, US1 — T015). Registro de ANÁLISIS:
 * una decisión por bloque, aire visual, líneas bajo 80 caracteres, radio 6px, Source Serif 4
 * (decidir si habilitar un medio nuevo es una decisión gerencial). Un momento de animación
 * deliberado al revelar el desglose de la intención no atendida por medio deseado, nunca hover por
 * fila. Sin Verde Rasero (La Regla del Registro Sin Dinero).
 *
 * La intención de compra no atendida es una MÉTRICA de cobertura (Lectura Crítica n.º 4), no un
 * faltante de inventario ni una `consulta_no_atendida` de 001.
 */

import { useEffect, useState, type FormEvent } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import {
  declararCobertura,
  listarMedios,
  obtenerCobertura,
  registrarIntencionNoAtendida,
  type MedioPago,
  type ResumenCobertura,
} from "../servicios/pagos";
import { etiquetaMedioPago, formatearPorcentaje } from "../utilidades/formato";
import estilos from "./CoberturaPago.module.css";

export function CoberturaPago({ idSucursal, idOperador }: { idSucursal: number; idOperador: number }) {
  const [medios, setMedios] = useState<MedioPago[]>([]);
  const [resumen, setResumen] = useState<ResumenCobertura | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmado, setConfirmado] = useState<string | null>(null);

  const [medioDeclarar, setMedioDeclarar] = useState("");
  const [aceptar, setAceptar] = useState(true);
  const [fechaDesde, setFechaDesde] = useState(new Date().toISOString().slice(0, 10));
  const [medioIntencion, setMedioIntencion] = useState("");

  function recargar() {
    setError(null);
    obtenerCobertura(idSucursal)
      .then(setResumen)
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudo cargar la cobertura.")
      );
  }

  useEffect(() => {
    listarMedios().then(setMedios).catch(() => setMedios([]));
  }, []);
  useEffect(recargar, [idSucursal]);

  async function declarar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    try {
      await declararCobertura({
        id_sucursal: idSucursal,
        id_medio_pago: Number(medioDeclarar),
        acepta: aceptar,
        fecha_desde: fechaDesde,
        id_operador: idOperador,
      });
      setConfirmado("Cobertura actualizada.");
      setTimeout(() => setConfirmado(null), 1600);
      recargar();
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo actualizar la cobertura.");
    }
  }

  async function registrarIntencion(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    try {
      await registrarIntencionNoAtendida({
        id_sucursal: idSucursal,
        id_medio_pago_deseado: Number(medioIntencion),
        id_operador: idOperador,
        clave_idempotencia: `ina-${idSucursal}-${Date.now()}`,
      });
      setConfirmado("Intención no atendida registrada.");
      setTimeout(() => setConfirmado(null), 1600);
      recargar();
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo registrar el evento.");
    }
  }

  return (
    <div className={estilos.pantalla}>
      <div className={estilos.encabezado}>
        <h2 className={estilos.titulo}>Cobertura de medios de pago</h2>
        <p className={estilos.subtitulo}>
          Qué medios acepta esta sucursal y cuánta intención de compra se pierde cuando un
          cliente no puede pagar como quería. Es una métrica de cobertura, no un faltante.
        </p>
      </div>

      <div className={estilos.cuerpo}>
        <section className={estilos.bloque}>
          <h3 className={estilos.bloqueTitulo}>Declarar qué acepta la sucursal</h3>
          <form className={estilos.form} onSubmit={declarar}>
            <label className={estilos.campo}>
              Medio de pago
              <select
                className={estilos.select}
                value={medioDeclarar}
                onChange={(e) => setMedioDeclarar(e.target.value)}
                required
              >
                <option value="">Elegir…</option>
                {medios.map((m) => (
                  <option key={m.id_medio_pago} value={m.id_medio_pago}>
                    {etiquetaMedioPago(m.nombre)}
                  </option>
                ))}
              </select>
            </label>
            <label className={estilos.campo}>
              Acción
              <select
                className={estilos.select}
                value={aceptar ? "acepta" : "deja"}
                onChange={(e) => setAceptar(e.target.value === "acepta")}
              >
                <option value="acepta">acepta desde</option>
                <option value="deja">deja de aceptar desde</option>
              </select>
            </label>
            <label className={estilos.campo}>
              Fecha
              <input
                className={estilos.entrada}
                type="date"
                value={fechaDesde}
                onChange={(e) => setFechaDesde(e.target.value)}
                required
              />
            </label>
            <button className={estilos.boton} type="submit">
              Guardar
            </button>
            {confirmado && <span className={estilos.confirmado}>{confirmado}</span>}
          </form>
          {error && <p className={estilos.error}>{error}</p>}
        </section>

        <section className={estilos.bloque}>
          <h3 className={estilos.bloqueTitulo}>Registrar una compra no completada por el medio de pago</h3>
          <form className={estilos.form} onSubmit={registrarIntencion}>
            <label className={estilos.campo}>
              Medio de pago deseado por el cliente
              <select
                className={estilos.select}
                value={medioIntencion}
                onChange={(e) => setMedioIntencion(e.target.value)}
                required
              >
                <option value="">Elegir…</option>
                {medios.map((m) => (
                  <option key={m.id_medio_pago} value={m.id_medio_pago}>
                    {etiquetaMedioPago(m.nombre)}
                  </option>
                ))}
              </select>
            </label>
            <button className={estilos.boton} type="submit">
              Registrar
            </button>
          </form>
        </section>

        {resumen && (
          <section className={`${estilos.bloque} ${estilos.animacionRevelar}`} key={resumen.periodo}>
            <h3 className={estilos.bloqueTitulo}>
              Cobertura y cuota de intención no atendida ({resumen.periodo})
            </h3>
            <table className={estilos.tabla}>
              <thead>
                <tr>
                  <th>Medio</th>
                  <th>¿Cubierto?</th>
                  <th>Intención no atendida</th>
                  <th>Cuota del período</th>
                </tr>
              </thead>
              <tbody>
                {resumen.medios.map((m) => (
                  <tr key={m.id_medio_pago}>
                    <td>{etiquetaMedioPago(m.nombre)}</td>
                    <td className={m.cubierto ? estilos.cubierto : estilos.noCubierto}>
                      {m.cubierto ? "sí" : "no"}
                    </td>
                    <td>{m.intencion_no_atendida}</td>
                    <td className={estilos.estimado}>
                      {formatearPorcentaje(m.cuota_no_atendida)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className={estilos.subtitulo}>
              La cuota es un valor calculado sobre {resumen.total_intencion_no_atendida} evento
              {resumen.total_intencion_no_atendida === 1 ? "" : "s"} del período.
            </p>
          </section>
        )}
      </div>
    </div>
  );
}
