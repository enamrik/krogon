#!/usr/bin/env bash

INIT_VERSION=$1

function latest_tag(){
  local TAG=$(git describe --tags --abbrev=0 2>/dev/null)
  echo "$TAG"
}

function increment_patch(){
    PARTS[2]=$(( PARTS[2] + 1 ))
}

function compose(){
  MAJOR="${PARTS[0]}"
  MINOR=".${PARTS[1]}"
  PATCH=".${PARTS[2]}"
  echo "${MAJOR}${MINOR}${PATCH}"
}

TAG=$(latest_tag)

if [[ -z "${TAG// }" ]]; then
  NEW_TAG=${INIT_VERSION}
  echo No tags found. Using tag ${NEW_TAG}
else
  PARTS=( ${TAG//./ } )
  increment_patch
  NEW_TAG=$(compose)
  echo Going from ${TAG} to ${NEW_TAG}
fi

echo ${NEW_TAG} > ./krogon/VERSION
git add ./krogon/VERSION && git commit -m "Release ${NEW_TAG}"
git tag -a ${NEW_TAG} -m "${NEW_TAG}"