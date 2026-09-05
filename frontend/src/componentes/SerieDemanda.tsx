/**
 * Serie de demanda observada vs corregida por quiebre de stock (T018, User Story 1 de
 * 004-pronostico-demanda). Registro de Análisis.
 *
 * La constitución exige distinguir SIEMPRE el dato observado del valor estimado, con tres
 * portadores simultáneos y nunca sólo color (plan.md, "Sistema de diseño en el frontend"):
 *   - demanda OBSERVADA: tinta normal, cifras tabulares.
 *   - demanda CORREGIDA: color `estimado` (#1F5673) + punto hueco + texto, con la nota de qué
 *     corrección se aplicó (quiebre + método base o sustituto, precio, promoción).
 *   - "no estimable por censura total" (FR-012): texto explícito en color estimado, nunca un 0.
 *
 * Cubre los cuatro ejes: quiebre (User Story 1), precio (User Story 4), promoción (User Story 5,
 * gancho a 005) y señal de sustitución (User Story 6).
 */

import { useEffect, useState } from "react";
import { ErrorApi } from "../servicios/clienteHttp";
import { obtenerSerieDemanda, type PuntoSerie } from "../servicios/pronostico";
import estilos from "./SerieDemanda.module.css";

function textoRespaldo(respaldo: PuntoSerie["respaldo_quiebre"]): string {
  if (respaldo === "consulta_no_atendida") return "respaldado por consultas no atendidas";
  return "método base";
}

function NotasPeriodo({ punto }: { punto: PuntoSerie }) {
  const notas: string[] = [];
  const ajusteSustituto = Number(punto.ajuste_cruzado_sustituto);
  if (ajusteSustituto > 0) {
    notas.push(`+${ajusteSustituto.toFixed(0)} por quiebre de un sustituto`);
  }
  const correccionPrecio = Number(punto.correccion_precio);
  if (correccionPrecio !== 0 && punto.precio_vigente_periodo) {
    const signo = correccionPrecio > 0 ? "+" : "";
    notas.push(
      `precio del período $${punto.precio_vigente_periodo} → ${signo}${correccionPrecio.toFixed(0)} al normalizar (ε ${punto.elasticidad_usada})`
    );
  }
  if (punto.excluido_por_promocion) {
    notas.push("período excluido: promoción activa");
  }
  if (punto.senal_sustitucion) {
    notas.push(
      `demanda posiblemente inflada por el quiebre del producto #${punto.senal_sustitucion.id_producto_en_quiebre}`
    );
  }
  if (notas.length === 0) return <span className={estilos.igual}>—</span>;
  return <span className={estilos.notas}>{notas.join(" · ")}</span>;
}

function CeldaCorregida({ punto }: { punto: PuntoSerie }) {
  if (punto.estado === "no_estimable_censura_total") {
    return <span className={estilos.noEstimable}>no estimable por censura total</span>;
  }

  const observada = Number(punto.demanda_observada);
  const corregida = Number(punto.demanda_corregida);
  const correccion = Number(punto.correccion_quiebre);

  if (correccion <= 0) {
    return <span className={estilos.igual}>{corregida.toFixed(0)}</span>;
  }

  return (
    <>
      <span className={estilos.corregida}>
        <span className={estilos.puntoHueco} aria-hidden="true" />
        {corregida.toFixed(0)}
      </span>
      <span className={estilos.detalleCorreccion}>
        corregido por quiebre · +{(corregida - observada).toFixed(0)} · {textoRespaldo(punto.respaldo_quiebre)}
      </span>
    </>
  );
}

export function SerieDemanda({
  idProducto,
  idSucursal,
}: {
  idProducto: number;
  idSucursal: number;
}) {
  const [serie, setSerie] = useState<PuntoSerie[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    setCargando(true);
    setError(null);
    obtenerSerieDemanda(idSucursal, idProducto)
      .then(setSerie)
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudo cargar la serie de demanda.")
      )
      .finally(() => setCargando(false));
  }, [idProducto, idSucursal]);

  if (error) return <p className={estilos.error}>{error}</p>;
  if (cargando) return <p className={estilos.instruccion}>Cargando serie…</p>;
  if (serie.length === 0) {
    return (
      <p className={estilos.instruccion}>
        Este producto todavía no tiene demanda registrada en esta sucursal.
      </p>
    );
  }

  const diasCorregidos = serie.filter((p) => Number(p.correccion_quiebre) > 0).length;

  return (
    <div className={estilos.contenedor}>
      <p className={estilos.resumen}>
        Demanda diaria observada y su corrección por quiebre de stock. Los días sin existencia se
        estiman a partir del máximo de los días recientes sin quiebre; nunca por debajo de lo
        observado.{" "}
        {diasCorregidos > 0
          ? `${diasCorregidos} día(s) corregido(s) en la ventana.`
          : "Sin días corregidos en la ventana."}
      </p>
      <table className={estilos.tabla}>
        <thead>
          <tr>
            <th>Día</th>
            <th>Observada</th>
            <th>Corregida</th>
            <th>Notas</th>
          </tr>
        </thead>
        <tbody>
          {serie.map((punto) => (
            <tr
              key={punto.periodo}
              className={Number(punto.dias_en_quiebre) > 0 ? estilos.filaQuiebre : undefined}
            >
              <td>{punto.periodo}</td>
              <td className={estilos.observada}>{Number(punto.demanda_observada).toFixed(0)}</td>
              <td>
                <CeldaCorregida punto={punto} />
              </td>
              <td>
                <NotasPeriodo punto={punto} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
