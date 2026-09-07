/**
 * Gestión de operadores (User Story 10, Principio VI) — 6.ª pestaña de Administración, visible
 * SÓLO para el rol `admin` (el segmentado de `Administracion.tsx` no la ofrece a un encargado;
 * no es "aparece pero da error al guardar", igual que el atajo de creación de producto).
 *
 * Registro de ANÁLISIS (como el resto de Administración). El alta y la edición usan el
 * `ModalAdministrable` único (La Regla del Modal Administrable): campos nombre, selector de
 * sucursal (obligatorio), selector de rol (obligatorio) y, en el alta, PIN de 4 dígitos.
 *
 * El backend verifica el rol `admin` con `requiere_rol`; esta pantalla nunca es la única
 * defensa.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { EstadoVacio } from "../componentes/EstadoVacio";
import { EsqueletoLista } from "../componentes/Esqueleto";
import { ModalAdministrable } from "../componentes/ModalAdministrable";
import { Obligatorio } from "../componentes/Obligatorio";
import { ErrorApi } from "../servicios/clienteHttp";
import {
  actualizarOperador,
  crearOperador,
  fijarActivoOperador,
  listarOperadores,
  type Operador,
} from "../servicios/operadores";
import { listarSucursales, type Sucursal } from "../servicios/sucursales";
import type { Rol } from "../hooks/useRol";
import estilos from "./Administracion.module.css";

const ROLES: Rol[] = ["cajero", "encargado", "admin"];

interface Form {
  nombre: string;
  rol: Rol;
  id_sucursal: number | "";
  pin: string;
}

const FORM_VACIO: Form = { nombre: "", rol: "cajero", id_sucursal: "", pin: "" };

export function GestionOperadores() {
  const [operadores, setOperadores] = useState<Operador[]>([]);
  const [sucursales, setSucursales] = useState<Sucursal[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [modal, setModal] = useState<{ operador?: Operador } | null>(null);
  const [form, setForm] = useState<Form>(FORM_VACIO);
  const [guardando, setGuardando] = useState(false);
  const [errorModal, setErrorModal] = useState<string | null>(null);

  const nombreSucursal = useCallback(
    (id: number) => sucursales.find((s) => s.id_sucursal === id)?.nombre ?? `Sucursal ${id}`,
    [sucursales],
  );

  const recargar = useCallback(() => {
    setCargando(true);
    setError(null);
    listarOperadores()
      .then(setOperadores)
      .catch((e) =>
        setError(e instanceof ErrorApi ? e.message : "No se pudo cargar la lista de operadores."),
      )
      .finally(() => setCargando(false));
  }, []);

  useEffect(recargar, [recargar]);
  useEffect(() => {
    listarSucursales().then(setSucursales).catch(() => setSucursales([]));
  }, []);

  function abrir(operador?: Operador) {
    setForm(
      operador
        ? { nombre: operador.nombre, rol: operador.rol, id_sucursal: operador.id_sucursal, pin: "" }
        : FORM_VACIO,
    );
    setErrorModal(null);
    setModal({ operador });
  }

  const formValido = useMemo(
    () =>
      form.nombre.trim() !== "" &&
      form.id_sucursal !== "" &&
      (modal?.operador ? true : form.pin.length === 4),
    [form, modal],
  );

  async function guardar() {
    if (!modal || form.id_sucursal === "") return;
    setGuardando(true);
    setErrorModal(null);
    try {
      const cuerpo = {
        nombre: form.nombre.trim(),
        rol: form.rol,
        id_sucursal: Number(form.id_sucursal),
        pin: form.pin.length === 4 ? form.pin : undefined,
      };
      if (modal.operador) {
        await actualizarOperador(modal.operador.id_operador, cuerpo);
      } else {
        await crearOperador(cuerpo);
      }
      setModal(null);
      recargar();
    } catch (e) {
      setErrorModal(e instanceof ErrorApi ? e.message : "No se pudo guardar el operador.");
    } finally {
      setGuardando(false);
    }
  }

  async function fijarActivo(operador: Operador, activo: boolean) {
    try {
      await fijarActivoOperador(operador.id_operador, { activo });
      recargar();
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No se pudo cambiar el estado del operador.");
    }
  }

  return (
    <>
      <div className={estilos.barra}>
        <span />
        <button className={estilos.botonNuevo} onClick={() => abrir()}>
          + Nuevo operador
        </button>
      </div>

      {error && <p className={estilos.error}>{error}</p>}

      {cargando ? (
        <EsqueletoLista filas={4} registro="analisis" altoFila={48} />
      ) : operadores.length === 0 ? (
        <EstadoVacio
          glifo="lista"
          titulo="Todavía no hay operadores"
          descripcion="Aquí aparecerá cada operador del sistema, con su rol y su sucursal asignada. Usa «+ Nuevo operador» para crear el primero."
        />
      ) : (
        <div className={estilos.tablaContenedor}>
          <table className={estilos.tabla}>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Rol</th>
                <th>Sucursal</th>
                <th>Estado</th>
                <th aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {operadores.map((o) => (
                <tr key={o.id_operador}>
                  <td>{o.nombre}</td>
                  <td>{o.rol}</td>
                  <td>{nombreSucursal(o.id_sucursal)}</td>
                  <td>{o.activo === false ? "Desactivado" : "Activo"}</td>
                  <td className={estilos.acciones}>
                    <button className={estilos.accion} onClick={() => abrir(o)}>
                      Editar
                    </button>
                    {o.activo === false ? (
                      <button className={estilos.accion} onClick={() => fijarActivo(o, true)}>
                        Reactivar
                      </button>
                    ) : (
                      <button className={estilos.accion} onClick={() => fijarActivo(o, false)}>
                        Desactivar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modal && (
        <ModalAdministrable
          titulo={`${modal.operador ? "Editar" : "Nuevo"} operador`}
          onCerrar={() => setModal(null)}
          onGuardar={guardar}
          guardando={guardando}
          error={errorModal}
          primariaHabilitada={formValido}
        >
          <label className={estilos.campo}>
            <span className={estilos.campoEtiqueta}>
              Nombre <Obligatorio />
            </span>
            <input
              className={estilos.entrada}
              value={form.nombre}
              onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))}
            />
          </label>

          <label className={estilos.campo}>
            <span className={estilos.campoEtiqueta}>
              Rol <Obligatorio />
            </span>
            <select
              className={estilos.entrada}
              value={form.rol}
              onChange={(e) => setForm((f) => ({ ...f, rol: e.target.value as Rol }))}
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>

          <label className={estilos.campo}>
            <span className={estilos.campoEtiqueta}>
              Sucursal <Obligatorio />
            </span>
            <select
              className={estilos.entrada}
              value={String(form.id_sucursal)}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  id_sucursal: e.target.value === "" ? "" : Number(e.target.value),
                }))
              }
            >
              <option value="" disabled>
                Elige una sucursal
              </option>
              {sucursales.map((s) => (
                <option key={s.id_sucursal} value={s.id_sucursal}>
                  {s.nombre}
                </option>
              ))}
            </select>
          </label>

          <label className={estilos.campo}>
            <span className={estilos.campoEtiqueta}>
              PIN (4 dígitos) {modal.operador ? "" : <Obligatorio />}
            </span>
            <input
              className={estilos.entrada}
              type="password"
              inputMode="numeric"
              maxLength={4}
              placeholder={modal.operador ? "Dejar vacío para no cambiarlo" : ""}
              value={form.pin}
              onChange={(e) => setForm((f) => ({ ...f, pin: e.target.value.replace(/\D/g, "") }))}
            />
          </label>
        </ModalAdministrable>
      )}
    </>
  );
}
