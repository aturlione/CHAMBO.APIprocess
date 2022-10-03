# DEPLOY REQUIREMENTS

🚀
<br>

> Deploy requirements for IH-IT software
> <br>

## App name
    - satd-katari-geoprocesses

## Process name
    - satd-katari-geoprocesses

## App Template

    - Api (api.wsgi)

## System

    - Linux

## Environment

    - Dev
    - Prod

## Distribution

    - Main

## Url GIT

    - git@github.com:IHCantabria/SATD-KATARI.Apiprocess.git

## DNS

_Production_

    - apiprocess.ihcantabria.com/

_Development_

    - apiprocessdev.ihcantabria.com/

## Other settings


Select only if needed:

`_____________`

**Services to restart**

`apache2`

**Backup**

    - Tags
    - Snapshot
    - Clone/Backup

---

**Do you need any other configuration?**

* Instalar librería de sistema openjdk-11-jdk

* Ejecutar requirements.txt

* Crear carpeta: /dat/log/{{ process_name }}/

* Prod: Renombrar el fichero config.prod.json por config.json

* Dev: Renombrar el fichero config.dev.json por config.json

<br>

## Relationships

**What applications, services, or data sources is this application related to?**

`_______________________________________________________________________________`

## Credits

[IH Cantabria](https://github.com/IHCantabria)

## FAQ

- Document provided by the system administrators [David del Prado](https://ihcantabria.com/directorio-personal/tecnologo/david-del-prado-secadas/) y [Gloria Zamora](https://ihcantabria.com/directorio-personal/tecnologo/gloria-zamora/)
