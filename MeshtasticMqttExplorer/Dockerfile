# ── Stage 1: build ────────────────────────────────────────────
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

# Copy solution and restore dependencies first (better layer caching)
COPY Common/Common.csproj               Common/
COPY MeshtasticMqttExplorer/MeshtasticMqttExplorer.csproj  MeshtasticMqttExplorer/
RUN dotnet restore MeshtasticMqttExplorer/MeshtasticMqttExplorer.csproj

# Copy everything and publish
COPY . .
RUN dotnet publish MeshtasticMqttExplorer/MeshtasticMqttExplorer.csproj \
    -c Release -o /app/publish --no-restore

# ── Stage 2: runtime ──────────────────────────────────────────
FROM mcr.microsoft.com/dotnet/aspnet:9.0
WORKDIR /App
COPY --from=build /app/publish .
ENTRYPOINT ["dotnet", "MeshtasticMqttExplorer.dll"]