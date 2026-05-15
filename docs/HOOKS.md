# Hooks git del proyecto

## post-commit — Mirror automático a Drive

**Función**: copia automática del Diccionario (`datos/DiccionarioProveedoresCategoria.xlsx`)
del repo a Google Drive (`Maestro/`) tras cada commit que lo modifique.

**Por qué un hook y no el Diccionario directamente en Drive**:
- Mantiene el repo como source of truth (versionado git de cada edición de datos:
  `git log` / `git blame` sobre el Diccionario).
- Atomicidad: un commit puede combinar código + datos (ej. nuevo extractor + alta
  de artículos asociados).
- Drive sigue accesible como antes para consultas web, otros PCs, etc.

**Trade-off**: una edición hecha directamente en Drive (web u otro PC) se
sobreescribe con el próximo commit del repo. Aceptable porque el único editor
activo es Jaime desde su PC. Si esto cambia, revisar el modelo.

**MAESTRO no se mirror-ea**: `MAESTRO_PROVEEDORES.xlsx` está gitignored (repo
público + IBANs sensibles). El hook usa `git diff-tree`, que solo ve ficheros
versionados — MAESTRO nunca dispararía el mirror aunque se añadiera al hook. Su
sync sigue siendo manual.

## Single source of truth: el template versionado

El hook activo vive en `.git/hooks/post-commit`, que **git no versiona**. La
copia canónica y versionada es `docs/hooks-templates/post-commit.sample.sh`.

Regla: **el template es la fuente de verdad**. Si editas el hook activo
(`.git/hooks/post-commit`), copia el cambio de vuelta al template y commitéalo:

    cp .git/hooks/post-commit docs/hooks-templates/post-commit.sample.sh
    git add docs/hooks-templates/post-commit.sample.sh
    git commit -m "chore(hooks): actualizar template post-commit"

Si no lo haces, el hook activo y el template divergen sin rastro en git.

## Instalación tras git clone fresh

Los hooks no se versionan (`.git/hooks/` está fuera del árbol git). Tras clonar
el repo en un PC nuevo, o tras cualquier operación que reinicialice los hooks,
reinstalar con:

    cp docs/hooks-templates/post-commit.sample.sh .git/hooks/post-commit
    chmod +x .git/hooks/post-commit

## Verificación post-instalación

Editar trivialmente el Diccionario, commitearlo, y comprobar que tras el commit
aparece el mensaje `[post-commit] mirror OK: ...` y que el fichero en Drive
recibe la actualización. Si Drive no está montado, el hook avisa con
`[post-commit] Drive no montado: ... - skip` y NO rompe el commit (post-commit
es informativo: el commit ya está hecho cuando el hook corre).
