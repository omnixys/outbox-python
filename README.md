# omnixys-outbox

Omnixys shared transactional outbox package for reliable event publishing.

## Installation

```bash
pip install omnixys-outbox
```

## Features

- Transactional outbox pattern implementation
- Event publisher with retry support
- SQLAlchemy ORM models
- Processor for outbox message handling

## Usage

```python
from omnixys_outbox import OutboxProcessor, OutboxPublisher, OutboxRepository, OutboxMessageModel
```

## License

GPL-3.0-or-later
