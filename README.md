# presencia-web

Diagnóstico técnico de la web de un negocio. Trece comprobaciones reales sobre una web pública, una nota sobre 100 y los tres fallos que más cuestan. Sin dependencias, sin claves de API, sin coste.

```
python3 presencia_web.py https://ejemplo.es
```

```
ejemplo.es  ->  80/100

HTTP 200 · 1.67 s · 115.0 KB · movil si · telefono no

Los tres fallos que mas cuestan:
  · Sin telefono ni WhatsApp pulsable: Quien decide llamar tiene que copiar el numero a mano. Muchos no lo hacen.
```

Con informe HTML:

```
python3 presencia_web.py https://ejemplo.es --html informe.html
```

## Qué mide

| Comprobación | Puntos |
|---|---|
| La web responde y el certificado es válido | 15 |
| Carga en menos de 2,5 s | 10 |
| Adaptada al móvil (etiqueta viewport) | 15 |
| Teléfono o WhatsApp pulsable | 10 |
| Título y descripción para Google | 8 |
| Aviso legal (LSSI) | 7 |
| Política de privacidad (RGPD) | 5 |
| Aviso de cookies | 5 |
| Un solo H1 | 5 |
| Al menos 300 palabras de contenido | 10 |
| Una llamada a la acción clara | 5 |
| Datos estructurados de negocio local | 5 |
| Imágenes con texto alternativo | aviso |

Además comprueba SPF y DMARC del dominio, que es lo que decide si tus correos llegan a la bandeja de entrada o a spam.

## Qué NO mide, y es importante

- **La ficha de Google.** Ni las reseñas, ni la nota media, ni si la ficha está completa. Esa parte no se puede sacar de la web: hay que consultarla negocio a negocio.
- **La posición real en Google** al buscar lo que el negocio vende.
- **Si el teléfono lo coge alguien.**

El informe declara esas tres cosas como no comprobadas en lugar de estimarlas. Un diagnóstico que rellena huecos con suposiciones no sirve para decidir nada.

## Por qué esta rúbrica y no otra

Los puntos no están repartidos por gusto. Pesan más las cosas que hacen perder clientes hoy: que la web no cargue, que en el móvil no se pueda usar, que no haya forma de llamar. Lo legal pesa porque es sancionable y arreglarlo es barato.

Es dura a propósito y a veces da notas bajas a webs que parecen correctas. Eso es información, no un fallo.

## Un aviso sobre el motor de descarga

Usa `curl` y no `urllib` a propósito. Con `urllib`, algunos servidores con WAF cierran la conexión y la herramienta informaría de que la web está caída cuando responde 200. Ese falso positivo ya ocurrió durante el desarrollo y es la peor clase de error que puede cometer un informe: acusar a alguien de algo que no pasa.

Si `curl` no está instalado, instálalo (`apt install curl`) o adapta la función `descarga()`.

## Requisitos

- Python 3.8 o superior
- `curl` y `host` (paquetes `curl` y `dnsutils`)

Nada más. No hay `pip install`.

## Licencia

Apache 2.0. Úsalo, modifícalo y véndelo si quieres. Ver [LICENSE](LICENSE).

## Autor

Kelwin Correa · [github.com/kelwincorrea14-arch](https://github.com/kelwincorrea14-arch)
