/**
 * ImagenProducto: el fallback al ícono de familia de categoría (US12, FR-077).
 *
 * Prueba de COMPORTAMIENTO, no visual: qué renderiza el componente según haya URL, no haya, o
 * la haya y el `<img>` falle al cargar.
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ImagenProducto } from "./ImagenProducto";

describe("ImagenProducto", () => {
  it("sin urlImagen muestra el ícono de categoría, nunca un <img>", () => {
    const { container } = render(
      <ImagenProducto urlImagen={null} nombreCategoria="Bebidas" nombreProducto="Jugo Natural 1L" />,
    );
    expect(container.querySelector("img")).toBeNull();
    // El ícono de categoría es un <svg> de línea (La Regla del Ícono).
    expect(container.querySelector("svg")).not.toBeNull();
  });

  it("con urlImagen válida renderiza el <img> con su alt", () => {
    render(
      <ImagenProducto
        urlImagen="https://cdn.example.com/jugo.jpg"
        nombreCategoria="Bebidas"
        nombreProducto="Jugo Natural 1L"
      />,
    );
    const img = screen.getByRole("img", { name: "Jugo Natural 1L" });
    expect(img).toHaveAttribute("src", "https://cdn.example.com/jugo.jpg");
  });

  it("si el <img> dispara onError cae al ícono de categoría y quita el <img>", () => {
    const { container } = render(
      <ImagenProducto
        urlImagen="https://cdn.example.com/rota.jpg"
        nombreCategoria="Limpieza"
        nombreProducto="Detergente 1kg"
      />,
    );
    const img = container.querySelector("img");
    expect(img).not.toBeNull();

    fireEvent.error(img!);

    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("svg")).not.toBeNull();
  });

  it("una urlImagen nueva vuelve a intentar la imagen tras un fallo previo", () => {
    const { container, rerender } = render(
      <ImagenProducto
        urlImagen="https://cdn.example.com/rota.jpg"
        nombreCategoria="Frescos"
        nombreProducto="Queso Fresco 500g"
      />,
    );
    fireEvent.error(container.querySelector("img")!);
    expect(container.querySelector("img")).toBeNull();

    rerender(
      <ImagenProducto
        urlImagen="https://cdn.example.com/nueva.jpg"
        nombreCategoria="Frescos"
        nombreProducto="Queso Fresco 500g"
      />,
    );
    expect(container.querySelector("img")).not.toBeNull();
  });
});
