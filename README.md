# STRAVA Heatmap cache

Скрипт предназначен для кэширования тайлов тепловой карты Strava с целью использования
их в приложении OsmAnd в качестве оффлайн карты или в приложении JOSM также в качестве
слоя, помогающего при картографировании.

## Запуск в Docker контейнере

Для запуска в Docker-контейнере достаточно выполнить:

```bash
docker run --rm \
  -v /var/strava-cache:/app/cache \
  --env KEY_PAIR_ID=CloudFront-Key-Pair-Id_from_cookies \
  --env SIGNATURE=CloudFront-Signature_from_cookies \
  --env POLICY=CloudFront-Policy_from_cookies \
  --name strava-heatmap-cache \
  denisbondar/strava-heatmap-cache
```

В качестве значений для переменных окружения `KEY_PAIR_ID`, `SIGNATURE`, `POLICY`
необходимо указать соответствующие значения, полученные из cookie на сайте
strava.com (после аутентификации).

Если у вас нет учётной записи на strava.com, то вы сможете загрузить только тайлы
масштаба не более 11.

## Использование в качествео оффлайн карты OsmAnd

1. Скопируйте каталог с кэшем на ваше андроид устройство в каталог
`/Android/data/net.osmand/files/tiles`. Желательно чтобы имя каталога было не
`cache`, а какое нибудь более понятное, например, `Strava heatmap`.
Так как файлов может быть очень много, то лучше создайте архив на компьютере,
скопируйте его на смартфон и там разархивируйте.

2. Откройте приложение OsmAnd. Меню - Настройки карты - Карта наложения.
Выберите Strava heatmap и укажите степень прозрачности. Или же включите опцию
"Показывать регулировку прозрачности", чтобы управлять ею прямо с карты.

## Использование в качестве слоя в JOSM

1. В JOSM в меню Слои - Настройки слоёв... в нижней части окна в списке
"Выбранные" нажмите кнопку **+TMS** и введите в п.4 готовый URL следующего вида:
`tms[17]:file:///var/strava-cache/{zoom}/{x}/{y}.png.tile`. Путь к кэшу указан
такой же, как и volume в примере запуска с использованием Docker, но у вас он
может быть каким угодно. В п.5 введите название слоя, например, `Strava Heatmap`.
Нажмите **ОК** в окне добавления подложки и **ОК** в окне настрек.

2. В меню Слои выберите слой **Strava Heatmap** - новый слой будет добавлен и
тайлы будут отображены на карте.

3. Рекомендуется немного размыть слой, т.к. границы тепловой карты могут быть
слишком резкими. Нажмите в списке слоев на слой **Strava Heatmap**, затем внизу
нажмите кнопку **Изменить видимость выбранного слоя** и настройте максимально
комфортную резкость. 

## Известные проблема и дорожная карта

На данный момент скрипт находится в стадии разработки, поэтому многие моменты в нем
могут показаться неочевидными или непонятными. Например:

1. На данный момент в скрипт жестко зашиты координаты Одесского региона.
Позже это будет вынесено в переменные окружения и в параметры командной строки,
если скрипт запускается не через Docker.

2. Остальные жестко зашитые параметры также будут вынесены.

3. Проблема с ограничением загрузки со стороны CloudFront. Сейчас она частично
решается при помощи семафора для асинхронного запуска и частично как ограничение
количества загружаемых тайлов за один раз. Но это всё равно не позволяет одним
запуском загрузить все тайлы во всех масштабах.

4. Планируется реализовать http-endpoint для загрузки тайлов по http из кэша
с возможностью наполнения кэша, если запрашиваемых тайлов в нем нет.

5. Планируется при прогреве кэша реализовать возможность перезагрузки тайлов,
если в кэше тайл устарел (старше ?? дней?)