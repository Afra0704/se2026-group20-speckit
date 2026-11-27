"""One-shot QA interruption with batch-size-only audit; no secret or answer logging."""
import json


def install_write_fault(marker, audit):
    from guided_notes.notes import routes
    from guided_notes.notes.sheets_gateway import GatewayError
    original = routes.gateway

    def load(path):
        return json.loads(path.read_text(encoding='utf-8'))

    def save(path, data):
        path.write_text(json.dumps(data), encoding='utf-8')

    class Gateway:
        def __init__(self, wrapped, teacher_id):
            self.wrapped, self.teacher_id = wrapped, teacher_id
            self.readback_blocked = False

        def __getattr__(self, name):
            return getattr(self.wrapped, name)

        def read_sheet(self, *args):
            if self.readback_blocked:
                state = load(audit)
                state['blocked_readbacks'] += 1
                save(audit, state)
                raise GatewayError('SOURCE_READ_UNAVAILABLE')
            return self.wrapped.read_sheet(*args)

        def write_unit(self, spreadsheet_id, sheet_id, writes):
            state = load(marker)
            if state.get('teacher_id') is None:
                state['teacher_id'] = self.teacher_id
            if state['teacher_id'] != self.teacher_id:
                return self.wrapped.write_unit(spreadsheet_id, sheet_id, writes)
            record = load(audit)
            state['attempts'] += 1
            if state['attempts'] == 2 and not state['injected']:
                state['injected'] = True
                save(marker, state)
                record['uncertain_batches'].append(len(writes))
                save(audit, record)
                self.readback_blocked = True
                # Intentionally unsent: caller cannot infer outcome and must read
                # before recovery. No production writer or database is modified.
                raise GatewayError('SOURCE_WRITE_UNCERTAIN', write_outcome='unknown')
            save(marker, state)
            result = self.wrapped.write_unit(spreadsheet_id, sheet_id, writes)
            record['actual_batches'].append(len(writes))
            save(audit, record)
            return result

    def gateway(teacher):
        wrapped = original(teacher)
        return Gateway(wrapped, teacher.teacher_id) if marker.is_file() else wrapped

    routes.gateway = gateway
