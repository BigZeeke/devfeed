/**
 * Dialog with one note field, used to save an article and to edit a saved note.
 *
 * The parent mounts it only while it is open, so each opening starts from
 * initialNote. onSave(note) must return a promise: on success the parent
 * closes the dialog; on failure the dialog shows the API's error message.
 */
import { useState } from 'react'
import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import DialogTitle from '@mui/material/DialogTitle'
import TextField from '@mui/material/TextField'

import { BOOKMARK_NOTE_MAX_LENGTH } from '../api.js'
import { describeFormError } from '../formErrors.js'

const NOTE_FIELD_NAMES = ['note']

function BookmarkNoteDialog({ dialogTitle, articleTitle, initialNote = '', saveButtonLabel, onCancel, onSave }) {
  const [noteInput, setNoteInput] = useState(initialNote)
  const [isSaving, setIsSaving] = useState(false)
  const [formError, setFormError] = useState({ fieldErrors: {}, generalMessage: null })

  const isNoteTooLong = noteInput.length > BOOKMARK_NOTE_MAX_LENGTH

  async function handleSubmit(event) {
    // Stop the browser's own form submit (a full page reload).
    event.preventDefault()
    setIsSaving(true)
    setFormError({ fieldErrors: {}, generalMessage: null })
    try {
      await onSave(noteInput)
    } catch (error) {
      setFormError(describeFormError(error, NOTE_FIELD_NAMES))
      setIsSaving(false)
    }
  }

  // The counter doubles as the helper text; an API error for the note replaces it.
  const noteHelperText =
    formError.fieldErrors.note ?? `${noteInput.length} / ${BOOKMARK_NOTE_MAX_LENGTH} characters`

  return (
    <Dialog
      open
      // Closing by Escape or a click outside is blocked while a save is in flight.
      onClose={isSaving ? undefined : onCancel}
      fullWidth
      maxWidth="sm"
      slotProps={{ paper: { component: 'form', onSubmit: handleSubmit, noValidate: true } }}
    >
      <DialogTitle>{dialogTitle}</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ marginBottom: 2 }}>{articleTitle}</DialogContentText>
        {formError.generalMessage && (
          <Alert severity="error" sx={{ marginBottom: 2 }}>
            {formError.generalMessage}
          </Alert>
        )}
        <TextField
          label="Note (optional)"
          name="note"
          value={noteInput}
          onChange={(event) => setNoteInput(event.target.value)}
          error={isNoteTooLong || Boolean(formError.fieldErrors.note)}
          helperText={noteHelperText}
          multiline
          minRows={3}
          fullWidth
          autoFocus
          sx={{ marginTop: 1 }}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel} disabled={isSaving}>
          Cancel
        </Button>
        <Button type="submit" variant="contained" disabled={isSaving || isNoteTooLong}>
          {isSaving ? 'Saving…' : saveButtonLabel}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default BookmarkNoteDialog
