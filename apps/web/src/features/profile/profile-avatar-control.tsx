import { useEffect, useId, useRef, useState } from 'react'
import { Camera, ImagePlus, LoaderCircle, Trash2, UserRound, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { AvatarCropDialog, type AvatarCropSource } from '@/features/profile/avatar-crop-dialog'
import {
  AVATAR_ACCEPT,
  validateAvatarSourceFile,
  type AvatarSourceError,
} from '@/features/profile/avatar-image'
import type { OwnProfile } from '@/features/profile/profile'
import {
  useRemoveProfilePhoto,
  useUploadProfilePhoto,
} from '@/features/profile/queries/use-profile-photo-mutations'
import { useProfilePhotoUrl } from '@/features/profile/queries/use-profile-photo-url'
import { ApiError } from '@/lib/api'

interface AvatarSelection {
  file: File
  previewUrl: string
  originalName: string
}

function ProfileAvatarControl({ profile }: { profile: OwnProfile }) {
  const { t } = useTranslation()
  const inputId = useId()
  const helpId = `${inputId}-help`
  const errorId = `${inputId}-error`
  const inputRef = useRef<HTMLInputElement>(null)
  const previewUrlRef = useRef<string | null>(null)
  const cropUrlRef = useRef<string | null>(null)
  const validationRequestRef = useRef(0)
  const [selection, setSelection] = useState<AvatarSelection | null>(null)
  const [cropSource, setCropSource] = useState<AvatarCropSource | null>(null)
  const [cropOpen, setCropOpen] = useState(false)
  const [clientError, setClientError] = useState<AvatarSourceError | null>(null)
  const [removeOpen, setRemoveOpen] = useState(false)
  const upload = useUploadProfilePhoto()
  const remove = useRemoveProfilePhoto()
  const avatarId = profile.avatar?.processing_status === 'READY' ? profile.avatar.id : null
  const currentPhoto = useProfilePhotoUrl(avatarId)
  const isPending = upload.isPending || remove.isPending

  useEffect(
    () => () => {
      validationRequestRef.current += 1
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current)
      if (cropUrlRef.current) URL.revokeObjectURL(cropUrlRef.current)
    },
    [],
  )

  const revokePreview = () => {
    if (!previewUrlRef.current) return
    URL.revokeObjectURL(previewUrlRef.current)
    previewUrlRef.current = null
  }

  const clearSelection = () => {
    revokePreview()
    setSelection(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  const closeCrop = () => {
    if (cropUrlRef.current) URL.revokeObjectURL(cropUrlRef.current)
    cropUrlRef.current = null
    setCropSource(null)
    setCropOpen(false)
  }

  const handleFileSelection = async (file: File | null) => {
    const requestId = validationRequestRef.current + 1
    validationRequestRef.current = requestId
    setClientError(null)
    upload.reset()
    remove.reset()
    if (!file) return

    const validationError = await validateAvatarSourceFile(file)
    if (validationRequestRef.current !== requestId) return
    if (validationError) {
      setClientError(validationError)
      return
    }

    closeCrop()
    const url = URL.createObjectURL(file)
    cropUrlRef.current = url
    setCropSource({ file, url })
    setCropOpen(true)
  }

  const uploadError =
    upload.error instanceof ApiError && upload.error.code === 'validation'
      ? t('profileAvatar.invalidImage')
      : t('profileAvatar.uploadError')
  const removeError = t('profileAvatar.removeError')
  const visibleError = clientError ? t(`profileAvatar.errors.${clientError}`) : null

  return (
    <section
      className="space-y-5 rounded-2xl border border-border/80 bg-muted/25 p-4 sm:p-5"
      aria-labelledby={`${inputId}-title`}
      aria-busy={isPending}
    >
      <div className="space-y-1">
        <h3 id={`${inputId}-title`} className="flex items-center gap-2 text-lg font-bold">
          <Camera className="size-5 text-vgu-orange" aria-hidden="true" />
          {t('profileAvatar.title')}
        </h3>
        <p id={helpId} className="text-sm leading-6 text-muted-foreground">
          {t('profileAvatar.help')}
        </p>
      </div>

      <div className="grid gap-5 md:grid-cols-[9rem_minmax(0,1fr)] md:items-start">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            {t('profileAvatar.current')}
          </p>
          <div className="relative flex size-32 items-center justify-center overflow-hidden rounded-full border-2 border-border bg-background shadow-sm">
            {currentPhoto.data ? (
              <img
                src={currentPhoto.data.url}
                alt={t('profileAvatar.currentAlt')}
                className="size-full object-cover"
                referrerPolicy="no-referrer"
                onError={() => void currentPhoto.refetch()}
              />
            ) : (
              <div
                className="flex size-full items-center justify-center text-muted-foreground"
                role="img"
                aria-label={
                  avatarId
                    ? currentPhoto.isError
                      ? t('profileAvatar.currentUnavailable')
                      : t('profileAvatar.loadingCurrent')
                    : t('profileAvatar.noCurrent')
                }
              >
                <UserRound className="size-12" aria-hidden="true" />
              </div>
            )}
            {currentPhoto.isFetching && avatarId ? (
              <span
                className="absolute inset-0 flex items-center justify-center bg-black/35 text-white"
                role="status"
                aria-label={t('profileAvatar.loadingCurrent')}
              >
                <LoaderCircle
                  className="size-5 animate-spin motion-reduce:animate-none"
                  aria-hidden="true"
                />
              </span>
            ) : null}
          </div>
          {currentPhoto.isError ? (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => void currentPhoto.refetch()}
            >
              {t('profileAvatar.retryCurrent')}
            </Button>
          ) : null}
        </div>

        <div className="space-y-4">
          <div className="space-y-2">
            <label htmlFor={inputId} className="text-sm font-semibold">
              {avatarId ? t('profileAvatar.replaceLabel') : t('profileAvatar.uploadLabel')}
            </label>
            <input
              ref={inputRef}
              id={inputId}
              type="file"
              accept={AVATAR_ACCEPT}
              disabled={isPending}
              aria-describedby={upload.isError || clientError ? `${helpId} ${errorId}` : helpId}
              className="block w-full rounded-lg border border-input bg-background text-sm text-foreground file:mr-3 file:border-0 file:bg-vgu-orange file:px-4 file:py-2.5 file:font-semibold file:text-vgu-black hover:file:bg-vgu-orange-light focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vgu-orange disabled:cursor-not-allowed disabled:opacity-60"
              onChange={(event) => {
                const file = event.target.files?.[0] ?? null
                event.currentTarget.value = ''
                void handleFileSelection(file)
              }}
            />
          </div>

          {selection ? (
            <div className="flex flex-col gap-3 rounded-xl border border-border bg-background p-3 sm:flex-row sm:items-center">
              <img
                src={selection.previewUrl}
                alt={t('profileAvatar.previewAlt')}
                className="size-20 shrink-0 rounded-xl object-cover"
              />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold">{selection.originalName}</p>
                <p className="text-xs text-muted-foreground">{t('profileAvatar.previewReady')}</p>
              </div>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                disabled={isPending}
                onClick={clearSelection}
              >
                <X aria-hidden="true" />
                {t('profileAvatar.clearSelection')}
              </Button>
            </div>
          ) : null}

          {visibleError ? (
            <p id={errorId} className="text-sm text-destructive" role="alert">
              {visibleError}
            </p>
          ) : upload.isError ? (
            <p id={errorId} className="text-sm text-destructive" role="alert">
              {uploadError}
            </p>
          ) : upload.isSuccess ? (
            <p className="text-sm font-medium text-emerald-600" role="status">
              {t('profileAvatar.uploaded')}
            </p>
          ) : remove.isSuccess ? (
            <p className="text-sm font-medium text-emerald-600" role="status">
              {t('profileAvatar.removed')}
            </p>
          ) : null}

          <div className="flex flex-wrap gap-3">
            <Button
              type="button"
              disabled={!selection || isPending}
              onClick={() => {
                if (!selection) return
                upload.mutate(selection.file, { onSuccess: clearSelection })
              }}
            >
              {upload.isPending ? (
                <LoaderCircle
                  className="animate-spin motion-reduce:animate-none"
                  aria-hidden="true"
                />
              ) : (
                <ImagePlus aria-hidden="true" />
              )}
              {upload.isPending
                ? t('profileAvatar.uploading')
                : upload.isError
                  ? t('profileAvatar.retryUpload')
                  : t('profileAvatar.upload')}
            </Button>
            {avatarId ? (
              <Button
                type="button"
                variant="destructive"
                disabled={isPending}
                onClick={() => {
                  remove.reset()
                  setRemoveOpen(true)
                }}
              >
                <Trash2 aria-hidden="true" />
                {t('profileAvatar.remove')}
              </Button>
            ) : null}
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={removeOpen}
        onOpenChange={(open) => {
          if (!open) remove.reset()
          setRemoveOpen(open)
        }}
        onConfirm={() => {
          if (!avatarId) return
          remove.mutate(avatarId, {
            onSuccess: () => {
              clearSelection()
              setRemoveOpen(false)
            },
          })
        }}
        title={t('profileAvatar.removeTitle')}
        description={t('profileAvatar.removeDescription')}
        confirmLabel={t('profileAvatar.confirmRemove')}
        cancelLabel={t('profileAvatar.keepPhoto')}
        pendingLabel={t('profileAvatar.removing')}
        error={remove.isError ? removeError : undefined}
        destructive
        isPending={remove.isPending}
      />
      <AvatarCropDialog
        open={cropOpen}
        source={cropSource}
        onCancel={closeCrop}
        onApply={(file) => {
          const originalName = cropSource?.file.name ?? file.name
          revokePreview()
          const previewUrl = URL.createObjectURL(file)
          previewUrlRef.current = previewUrl
          setSelection({ file, previewUrl, originalName })
          setClientError(null)
          closeCrop()
        }}
      />
    </section>
  )
}

export { ProfileAvatarControl }
