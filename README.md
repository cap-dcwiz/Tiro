# Tiro

The complete toolchain for DCWiz data interface development, data validation, data exchanging and mock data generation

## Usage

There are some sample data and configuration in the `/demo` directory.

### Generating data schema and examples

```bash
tiro schema show config/scenario.yaml config/use1.yaml
tiro schema example config/scenario.yaml config/use1.yaml
```

### Launch mock data generator
```bash
tiro mock serve config/scenario.yaml config/use1.yaml
```
The documentation for the generator will be on `http://127.0.0.1:8000/docs`

### Launch a individual validation server
```bash
tiro validate serve config/scenario.yaml config/use1.yaml
```
The documentation for the validator will be on `http://127.0.0.1:8000/docs`

### Launch a Karez data collection framework including the data storage, validator and data generator.
```bash
docker compose -f tiro_mock.docker-compose.yml up -d --build
```